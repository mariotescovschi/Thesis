import { useEffect, useState } from 'react';

type Status = 'loading' | 'loaded' | 'failed';

export const useImage = (url: string): [HTMLImageElement | null, Status] => {
  const [state, setState] = useState<{ url: string; img: HTMLImageElement | null; status: Status }>(
    { url, img: null, status: 'loading' },
  );

  useEffect(() => {
    let active = true;
    const image = new window.Image();
    image.crossOrigin = 'anonymous';
    image.onload = () => active && setState({ url, img: image, status: 'loaded' });
    image.onerror = () => active && setState({ url, img: null, status: 'failed' });
    image.src = url;
    return () => {
      active = false;
    };
  }, [url]);

  // When the url just changed, the stored state still describes the previous image.
  if (state.url !== url) return [null, 'loading'];
  return [state.img, state.status];
};
