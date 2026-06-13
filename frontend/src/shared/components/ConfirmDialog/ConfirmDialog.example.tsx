/**
 * ConfirmDialog 使用示例
 * 展示不同变体的确认弹窗
 */

import { useState } from 'react';
import { ConfirmDialog } from './ConfirmDialog';

export function ConfirmDialogExample() {
  const [showInfoDialog, setShowInfoDialog] = useState(false);
  const [showWarningDialog, setShowWarningDialog] = useState(false);
  const [showDangerDialog, setShowDangerDialog] = useState(false);
  const [showLoadingDialog, setShowLoadingDialog] = useState(false);

  const handleConfirm = (variant: string) => {
    console.log(`确认操作: ${variant}`);
    setShowInfoDialog(false);
    setShowWarningDialog(false);
    setShowDangerDialog(false);
    setShowLoadingDialog(false);
  };

  return (
    <div style={{ padding: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <button onClick={() => setShowInfoDialog(true)}>信息确认弹窗</button>
      <button onClick={() => setShowWarningDialog(true)}>警告确认弹窗</button>
      <button onClick={() => setShowDangerDialog(true)}>危险确认弹窗</button>
      <button onClick={() => setShowLoadingDialog(true)}>加载状态弹窗</button>

      <ConfirmDialog
        isOpen={showInfoDialog}
        onClose={() => setShowInfoDialog(false)}
        onConfirm={() => handleConfirm('info')}
        title="确认操作"
        message="这是一个信息确认弹窗，用于一般性的确认操作。"
        confirmText="确认"
        cancelText="取消"
        variant="info"
      />

      <ConfirmDialog
        isOpen={showWarningDialog}
        onClose={() => setShowWarningDialog(false)}
        onConfirm={() => handleConfirm('warning')}
        title="警告确认"
        message="此操作可能会影响系统性能，请确认是否继续？"
        confirmText="继续"
        cancelText="取消"
        variant="warning"
      />

      <ConfirmDialog
        isOpen={showDangerDialog}
        onClose={() => setShowDangerDialog(false)}
        onConfirm={() => handleConfirm('danger')}
        title="删除确认"
        message="此操作将永久删除数据，且无法恢复。确定要继续吗？"
        confirmText="删除"
        cancelText="取消"
        variant="danger"
      />

      <ConfirmDialog
        isOpen={showLoadingDialog}
        onClose={() => setShowLoadingDialog(false)}
        onConfirm={() => {
          // 模拟异步操作
          setTimeout(() => {
            setShowLoadingDialog(false);
          }, 2000);
        }}
        title="处理中"
        message="正在处理您的请求，请稍候..."
        confirmText="确认"
        cancelText="取消"
        loading={showLoadingDialog}
      />
    </div>
  );
}
