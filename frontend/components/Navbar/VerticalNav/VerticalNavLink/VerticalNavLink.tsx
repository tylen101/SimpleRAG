import Link from 'next/link';
import React, { ReactNode } from 'react';
import styles from './VerticalNavLink.module.css';

type VerticalNavLinkProps = {
  href: string;
  text?: string;
  icon?: ReactNode;
  collapsed: boolean;
  active: boolean;
};

export default function VerticalNavLink({
  href,
  text,
  icon,
  collapsed,
  active,
}: VerticalNavLinkProps) {
  return (
    <Link
      href={href}
      className={`${styles.navItem} ${collapsed ? styles.collapsed : ''} ${
        active ? styles.active : ''
      }`}
      title={text}
    >
      {active && <div className={styles.activeLink} />}
      <span className={styles.iconSlot}>{icon}</span>
      <span className={styles.text}>{text}</span>
    </Link>
  );
}
