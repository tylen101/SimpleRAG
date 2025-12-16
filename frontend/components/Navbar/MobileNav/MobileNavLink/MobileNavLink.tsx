import Link from 'next/link';
import React, { ReactNode } from 'react';

import styles from './MobileNavLink.module.css';

type MobileNavLinkProps = {
  href: string;
  text?: string;
  icon?: ReactNode;
  active: boolean;
};

function MobileNavLink({ href, text, icon, active }: MobileNavLinkProps) {
  return (
    <Link
      href={href}
      className={`${styles.navItem} ${active ? styles.active : ''}`}
      title={text}
    >
      {active && <div className={styles.activeLink} />}
      <span className={styles.iconSlot}>{icon}</span>
      <span className={styles.text}>{text}</span>
    </Link>
  );
}

export default MobileNavLink;
