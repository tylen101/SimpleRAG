import { navLinks } from '@/data/routes';
import { usePathname } from 'next/navigation';
import React from 'react';
import MobileNavLink from './MobileNavLink/MobileNavLink';
import { helpIcon } from '@/icons/helpIcon';

import styles from './MobileNav.module.css';

function MobileNav({}) {
  const pathname = usePathname();

  return (
    <div className={styles.mobileNavContainer}>
      {navLinks.map((link) => {
        return (
          <MobileNavLink
            key={link.title}
            text={link.title}
            href={link.url}
            icon={link.icon}
            active={pathname === link.url}
          />
        );
      })}
      <MobileNavLink
        key="/help"
        text="Help/FAQ"
        href="/help"
        icon={helpIcon}
        active={pathname === '/help'}
      />
    </div>
  );
}

export default MobileNav;
