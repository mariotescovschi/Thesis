import { type ComponentProps, type ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

interface FileRowProps extends ComponentProps<'button'> {
  icon: ReactNode;
  label: string;
  active?: boolean;
  trailing?: ReactNode;
}

export const FileRow = ({ icon, label, active, trailing, className, ...props }: FileRowProps) => (
  <button
    className={cn(
      'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] transition-colors',
      active
        ? 'bg-accent text-accent-foreground'
        : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
      className,
    )}
    {...props}
  >
    <span className="shrink-0 text-muted-foreground">{icon}</span>
    <span className="flex-1 truncate">{label}</span>
    {trailing}
  </button>
);
