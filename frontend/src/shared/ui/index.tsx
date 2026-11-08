import { forwardRef, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { X } from 'lucide-react';
export * as Tabs from '@radix-ui/react-tabs';
export * as DropdownMenu from '@radix-ui/react-dropdown-menu';
export * as ScrollArea from '@radix-ui/react-scroll-area';
export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'outline' | 'ghost' }>(({ className = '', variant = 'primary', type = 'button', ...props }, ref) => <button ref={ref} type={type} className={`button button-${variant} ${className}`} {...props} />);
Button.displayName = 'Button';
export function Badge(props: HTMLAttributes<HTMLSpanElement>) { return <span {...props} className={`badge ${props.className ?? ''}`} />; }
export function Card(props: HTMLAttributes<HTMLElement>) { return <section {...props} className={`card ${props.className ?? ''}`} />; }
export function Separator() { return <hr className="separator" />; }
export function Toggle({ pressed, onPressedChange, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { pressed: boolean; onPressedChange: (pressed: boolean) => void }) { return <Button variant="outline" {...props} aria-pressed={pressed} onClick={() => onPressedChange(!pressed)} />; }
export function Progress({ value, label }: { value: number; label: string }) { const safe = Math.max(0, Math.min(100, value)); return <div className="progress" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={safe}><div style={{ width: `${safe}%` }} /></div>; }
export function Tooltip({ children, content }: { children: ReactNode; content: string }) { return <TooltipPrimitive.Provider delayDuration={200}><TooltipPrimitive.Root><TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger><TooltipPrimitive.Portal><TooltipPrimitive.Content className="tooltip" sideOffset={6}>{content}</TooltipPrimitive.Content></TooltipPrimitive.Portal></TooltipPrimitive.Root></TooltipPrimitive.Provider>; }
export function Dialog({ trigger, title, children }: { trigger: ReactNode; title: string; children: ReactNode }) { return <DialogPrimitive.Root><DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger><DialogPrimitive.Portal><DialogPrimitive.Overlay className="dialog-overlay"/><DialogPrimitive.Content className="dialog-content" aria-describedby={undefined}><DialogPrimitive.Title>{title}</DialogPrimitive.Title>{children}<DialogPrimitive.Close asChild><Button variant="ghost" aria-label="Close dialog"><X size={18}/></Button></DialogPrimitive.Close></DialogPrimitive.Content></DialogPrimitive.Portal></DialogPrimitive.Root>; }
