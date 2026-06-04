import { InputHTMLAttributes, ReactNode } from 'react';
import styles from './Input.module.css';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: ReactNode;
}

export function Input({ icon, className = '', ...props }: InputProps) {
  return (
    <div className={`${styles.inputWrapper} ${className}`}>
      {icon && <span>{icon}</span>}
      <input className={styles.input} {...props} />
    </div>
  );
}
