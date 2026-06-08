import { Icon } from '../Icon';
import type {
  NavigationType,
  GroupChatNavigationData,
  CreateSingleChatNavigationData,
} from '../../utils/navigationParser';
import styles from './NavigationCard.module.css';

export interface NavigationCardProps {
  type: NavigationType;
  data: GroupChatNavigationData | CreateSingleChatNavigationData;
  linkText: string;
  onNavigate: () => void;
}

export function NavigationCard({ type, data, linkText, onNavigate }: NavigationCardProps) {
  const isGroupChat = type === 'group_chat';

  return (
    <div
      className={`${styles.card} ${isGroupChat ? styles.cardGroupChat : styles.cardSingleChat}`}
      onClick={onNavigate}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onNavigate();
      }}
    >
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <Icon size={18}>
            {isGroupChat ? (
              <>
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </>
            ) : (
              <>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </>
            )}
          </Icon>
        </div>
        <div className={styles.titleGroup}>
          <div className={styles.title}>
            {isGroupChat
              ? (data as GroupChatNavigationData).name
              : (data as CreateSingleChatNavigationData).agent_name}
          </div>
          <div className={styles.subtitle}>
            {isGroupChat
              ? `${(data as GroupChatNavigationData).members.length} 个成员`
              : (data as CreateSingleChatNavigationData).description}
          </div>
        </div>
      </div>

      {isGroupChat && (
        <div className={styles.members}>
          {(data as GroupChatNavigationData).members.map((member) => (
            <span key={member} className={styles.memberBadge}>
              {member}
            </span>
          ))}
        </div>
      )}

      <div className={styles.actions}>
        <button className={styles.navButton} onClick={onNavigate}>
          <Icon size={14}>
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </Icon>
          {linkText}
        </button>
      </div>
    </div>
  );
}
