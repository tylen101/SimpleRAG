import React, { useState } from 'react';
import styles from './VerticalNav.module.css';
import { collapseIcon } from '@/icons/collapseIcon';
import VerticalNavLink from './VerticalNavLink/VerticalNavLink';
import { helpIcon } from '@/icons/helpIcon';
import { codeIcon } from '@/icons/codeIcon';
import { usePathname } from 'next/navigation';
import { navLinks } from '@/data/routes';

export default function VerticalNav() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <nav
      className={`${styles.verticalContainer} ${
        collapsed ? styles.collapsed : ''
      }`}
    >
      {/* brand or logo */}
      <div className={styles.brand}>
        {codeIcon}
        <span className={styles.brandText} title="Enterprise Knowledge System">
          EKS
        </span>
      </div>

      {/* nav stuff */}
      <div className={styles.navLinks}>
        {navLinks.map((link) => (
          <VerticalNavLink
            key={link.title}
            text={link.title}
            href={link.url}
            icon={link.icon}
            collapsed={collapsed}
            active={pathname === link.url}
          />
        ))}
      </div>

      {/* divider and help / FAQ */}
      <div className={styles.bottom}>
        <div className={styles.divider} />
        <VerticalNavLink
          key="/help"
          text="Help/FAQ"
          href="/help"
          icon={helpIcon}
          collapsed={collapsed}
          active={pathname === '/help'}
        />

        <button
          className={styles.collapseButton}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapseIcon}
        </button>
      </div>
      {/* open/close toggle (implement localstorage or save pref to user profile?)*/}
    </nav>
  );
}
