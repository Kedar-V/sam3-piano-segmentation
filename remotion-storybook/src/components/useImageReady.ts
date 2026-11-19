import {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender} from 'remotion';

/** Holds the render until an image is decoded, so CSS mask-images are never captured half-loaded. */
export const useImageReady = (src: string | null): boolean => {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!src) {
      setReady(true);
      return;
    }
    setReady(false);
    const handle = delayRender(`image ${src}`, {timeoutInMilliseconds: 60000});
    const img = new Image();
    img.onload = () => {
      // decode() makes sure the bitmap is ready for the very next paint
      (img.decode ? img.decode() : Promise.resolve()).catch(() => undefined).then(() => {
        setReady(true);
        continueRender(handle);
      });
    };
    img.onerror = () => cancelRender(new Error(`Failed to load ${src}`));
    img.src = src;
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [src]);
  return ready;
};
