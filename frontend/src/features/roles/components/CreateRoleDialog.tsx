/**
 * 创建角色弹窗组件
 */

import { useState, useEffect } from 'react';
import { AvatarSelector } from './AvatarSelector';
import { AccordionSection } from './AccordionSection';
import { useCreateRole } from '../hooks/useCreateRole';
import { SkillSelectorModal, ToolSelectorModal } from '@/shared/components';
import { getToolCatalog } from '@/core/api';
import type { CreateRoleFormData } from '../types';
import type { AgentPlatform, ToolGroupResponse } from '@/shared/types/api-schemas';
import styles from './CreateRoleDialog.module.css';

export interface CreateRoleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (newRoleName?: string) => void;
}

const platforms: { value: AgentPlatform; label: string }[] = [
  { value: 'claude', label: 'Claude' },
  { value: 'codex', label: 'Codex' },
  { value: 'opencode', label: 'OpenCode' },
];

export function CreateRoleDialog({ isOpen, onClose, onSuccess }: CreateRoleDialogProps) {
  const [formData, setFormData] = useState<CreateRoleFormData>({
    name: '',
    platform: 'claude',
    avatar: null,
    description: '',
    skills: [],
    enabled_tools: [],
  });

  const [expandedSections, setExpandedSections] = useState({
    platform: true,
    name: true,
    avatar: false,
    description: false,
    skills: false,
    tools: false,
  });

  const [showSkillSelector, setShowSkillSelector] = useState(false);
  const [showToolSelector, setShowToolSelector] = useState(false);
  const [toolCatalog, setToolCatalog] = useState<ToolGroupResponse[]>([]);

  const { createRole, submitting } = useCreateRole();

  // Load tool catalog when dialog opens and set all tools as enabled by default
  useEffect(() => {
    if (isOpen) {
      getToolCatalog().then((data) => {
        setToolCatalog(data.groups);
        // 默认启用所有工具
        const allToolNames = data.groups.flatMap((g) => g.tools.map((t) => t.name));
        setFormData((prev) => ({ ...prev, enabled_tools: allToolNames }));
      });
    }
  }, [isOpen]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      return;
    }

    const success = await createRole(formData);
    if (success) {
      onSuccess?.(formData.name);
      handleClose();
    }
  };

  const handleAddSkill = (skill: { name: string }) => {
    if (!formData.skills.includes(skill.name)) {
      setFormData((prev) => ({ ...prev, skills: [...prev.skills, skill.name] }));
    }
  };

  const handleRemoveSkill = (skillName: string) => {
    setFormData((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skillName),
    }));
  };

  const handleSaveTools = (enabled: string[]) => {
    setFormData((prev) => ({ ...prev, enabled_tools: enabled }));
  };

  const handleClose = () => {
    setFormData({ name: '', platform: 'claude', avatar: null, description: '', skills: [], enabled_tools: [] });
    setShowSkillSelector(false);
    setShowToolSelector(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>创建角色</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.mainContent}>
            {/* 左侧预览区 */}
            <div className={styles.previewPanel}>
              <div className={styles.previewAvatar}>
                {formData.avatar ? (
                  <div dangerouslySetInnerHTML={{ __html: formData.avatar }} />
                ) : (
                  <span>?</span>
                )}
              </div>
              <div className={styles.previewName}>{formData.name || '角色名称'}</div>
              <div className={styles.typeBadge}>{formData.platform}</div>
              <div className={styles.previewDesc}>{formData.description || '角色描述'}</div>
            </div>

            {/* 右侧选项区 */}
            <div className={styles.optionsPanel}>
              <AccordionSection
                title="平台选择"
                badge="必填"
                isOpen={expandedSections.platform}
                onToggle={() => toggleSection('platform')}
              >
                <div className={styles.platformGroup}>
                  {platforms.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      className={`${styles.platformBtn} ${formData.platform === p.value ? styles.selected : ''}`}
                      onClick={() => setFormData((prev) => ({ ...prev, platform: p.value }))}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </AccordionSection>

              <AccordionSection
                title="角色名称"
                badge="必填"
                isOpen={expandedSections.name}
                onToggle={() => toggleSection('name')}
              >
                <input
                  id="role-name"
                  type="text"
                  className={styles.inputEnhanced}
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="输入角色名称"
                  required
                />
              </AccordionSection>

              <AccordionSection
                title="头像选择"
                badge={formData.avatar ? '已选' : '可选'}
                isOpen={expandedSections.avatar}
                onToggle={() => toggleSection('avatar')}
              >
                <AvatarSelector
                  selectedAvatar={formData.avatar}
                  onSelect={(avatar) => setFormData((prev) => ({ ...prev, avatar }))}
                />
              </AccordionSection>

              <AccordionSection
                title="角色描述"
                badge="可选"
                isOpen={expandedSections.description}
                onToggle={() => toggleSection('description')}
              >
                <textarea
                  id="role-description"
                  className={styles.textarea}
                  value={formData.description}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, description: e.target.value }))
                  }
                  placeholder="输入角色描述（可选）"
                  rows={3}
                />
              </AccordionSection>

              <AccordionSection
                title="技能列表"
                badge={`${formData.skills.length} 个`}
                isOpen={expandedSections.skills}
                onToggle={() => toggleSection('skills')}
              >
                <div className={styles.skillsContainer}>
                  {formData.skills.length > 0 ? (
                    <div className={styles.skillsList}>
                      {formData.skills.map((skill) => (
                        <div key={skill} className={styles.skillItem}>
                          <span className={styles.skillName}>{skill}</span>
                          <button
                            type="button"
                            className={styles.removeSkillBtn}
                            onClick={() => handleRemoveSkill(skill)}
                            aria-label={`移除 ${skill}`}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.noSkills}>暂无技能</div>
                  )}
                  <button
                    type="button"
                    className={styles.addSkillBtn}
                    onClick={() => setShowSkillSelector(true)}
                  >
                    + 添加技能
                  </button>
                </div>
              </AccordionSection>

              <AccordionSection
                title="工具管理"
                badge={`${formData.enabled_tools.length} 个`}
                isOpen={expandedSections.tools}
                onToggle={() => toggleSection('tools')}
              >
                <div className={styles.skillsContainer}>
                  <div className={styles.skillsList}>
                    {formData.enabled_tools.length > 0 ? (
                      formData.enabled_tools.slice(0, 8).map((name) => (
                        <span key={name} className={styles.skillItem}>
                          {name}
                        </span>
                      ))
                    ) : (
                      <span className={styles.noSkills}>全部启用</span>
                    )}
                    {formData.enabled_tools.length > 8 && (
                      <span className={styles.skillItem}>+{formData.enabled_tools.length - 8}</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className={styles.addSkillBtn}
                    onClick={() => setShowToolSelector(true)}
                  >
                    + 管理工具
                  </button>
                </div>
              </AccordionSection>
            </div>
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button type="submit" className={styles.submitBtn} disabled={submitting}>
              {submitting ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>

      <SkillSelectorModal
        isOpen={showSkillSelector}
        onClose={() => setShowSkillSelector(false)}
        onSelect={handleAddSkill}
        excludeNames={formData.skills}
      />

      <ToolSelectorModal
        isOpen={showToolSelector}
        onClose={() => setShowToolSelector(false)}
        onSave={handleSaveTools}
        catalog={toolCatalog}
        disabledTools={toolCatalog
          .flatMap((g) => g.tools.map((t) => t.name))
          .filter((n) => !formData.enabled_tools.includes(n))}
      />
    </div>
  );
}
