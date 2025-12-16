import React from 'react';
import styles from './Button.module.css';

import { ReactNode } from 'react';

type ButtonProps = {
  text?: string;
  customClass?: string;
  style?: object;
  onClick: () => void;
  iconPosition?: 'left' | 'right';
  icon?: ReactNode;
};

function Button({ text, onClick, icon, customClass, style = {} }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      className={styles.buttonContainer + ` ` + customClass}
      style={{ ...style }}
    >
      {text}
      {icon}
    </button>
  );
}

export default Button;
