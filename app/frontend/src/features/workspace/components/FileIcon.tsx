import { useEffect, useState } from 'react';
import icons from '@exuanbo/file-icons-js/dist/js/file-icons.esm.js';

interface FileIconProps {
  filename: string;
  isDirectory?: boolean;
}

export const FileIcon = ({ filename, isDirectory }: FileIconProps) => {
  const [className, setClassName] = useState('');

  useEffect(() => {
    const name = isDirectory ? `${filename}/` : filename;
    icons.getClass(name).then((cls) => setClassName(cls || ''));
  }, [filename, isDirectory]);

  if (!className) return <span className="inline-block size-4" />;
  return <i className={className} style={{ fontSize: '16px' }} />;
};
