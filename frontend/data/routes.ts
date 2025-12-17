import { documentIcon } from '@/icons/documentIcon';
import { listIcon } from '@/icons/listIcon';
import { profileIcon } from '@/icons/profileIcon';
import { progressIcon } from '@/icons/progressIcon';

export const navLinks = [
  { title: 'Dashboard', url: '/dashboard', icon: listIcon },
  {
    title: 'Documents',
    url: '/documents',
    icon: documentIcon,
  },
  {
    title: 'Chat',
    url: '/chat',
    icon: progressIcon,
  },
  {
    title: 'Profile',
    url: '/profile',
    icon: profileIcon,
  },
];
