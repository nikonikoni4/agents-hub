import { useState, useMemo } from 'react';
import { SearchIcon } from '@/shared/components';
import type { ToolGroupResponse } from '@/shared/types/api-schemas';
import styles from './ToolSelectorModal.module.css';

export interface ToolSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (enabledTools: string[]) => void;
  catalog: ToolGroupResponse[];
  disabledTools: string[];
}

export function ToolSelectorModal({
  isOpen,
  onClose,
  onSave,
  catalog,
  disabledTools,
}: ToolSelectorModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [localDisabled, setLocalDisabled] = useState<Set<string>>(() => new Set(disabledTools));

  // Reset on open
  const [prevIsOpen, setPrevIsOpen] = useState(false);
  if (isOpen && !prevIsOpen) {
    setPrevIsOpen(true);
    setLocalDisabled(new Set(disabledTools));
  }
  if (!isOpen && prevIsOpen) {
    setPrevIsOpen(false);
  }

  const toggleTool = (name: string) => {
    setLocalDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const filteredGroups = useMemo(() => {
    if (!searchQuery) return catalog;
    const q = searchQuery.toLowerCase();
    return catalog
      .map((group) => ({
        ...group,
        tools: group.tools.filter(
          (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.tools.length > 0);
  }, [catalog, searchQuery]);

  const handleSave = () => {
    const allNames = catalog.flatMap((g) => g.tools.map((t) => t.name));
    const enabled = allNames.filter((n) => !localDisabled.has(n));
    onSave(enabled);
    onClose();
  };

  const handleClose = () => {
    setSearchQuery('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>工具管理</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.searchBox}>
          <SearchIcon />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="搜索工具..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className={styles.content}>
          {filteredGroups.map((group) => (
            <div key={group.name} className={styles.group}>
              <div className={styles.groupTitle}>
                <span>{group.icon}</span>
                <span>{group.name}</span>
              </div>
              <div className={styles.toolsGrid}>
                {group.tools.map((tool) => {
                  const isDisabled = localDisabled.has(tool.name);
                  return (
                    <button
                      key={tool.name}
                      type="button"
                      className={`${styles.toolCard} ${isDisabled ? styles.disabled : styles.enabled}`}
                      onClick={() => toggleTool(tool.name)}
                    >
                      <div className={styles.toolName}>{tool.name}</div>
                      <div className={styles.toolDesc}>{tool.description}</div>
                      <span className={isDisabled ? styles.badgeDisabled : styles.badgeEnabled}>
                        {isDisabled ? '已禁用' : '已启用'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.cancelBtn} onClick={handleClose}>
            取消
          </button>
          <button type="button" className={styles.saveBtn} onClick={handleSave}>
            确定
          </button>
        </div>
      </div>
    </div>
  );
}
