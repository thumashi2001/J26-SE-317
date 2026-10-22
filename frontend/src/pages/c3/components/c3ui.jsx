import React, { useEffect, useRef } from 'react';

// Small shared pieces for the marking pages. They only compose the global classes from index.css
// (.page-head, .pill, .btn, .tabs, .notice, .panel) so the marking pages match the rest of AdaptiveLearnSE.

export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-head c3-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="c3-actions">{actions}</div>}
    </header>
  );
}

const STATUS = {
  pending_review: { label: 'Awaiting review', cls: 'status-pending' },
  reviewed: { label: 'Reviewed', cls: 'c3-status-info' },
  finalized: { label: 'Finalized', cls: 'status-approved' },
  failed: { label: 'Failed', cls: 'status-rejected' },
};

// Shows the real backend state of a submission, nothing else.
export function StatusPill({ status }) {
  const s = STATUS[status || 'pending_review'] || { label: String(status), cls: 'c3-status-info' };
  return <span className={`pill ${s.cls}`}>{s.label}</span>;
}

export function Spinner({ label }) {
  return (
    <span className="c3-spin-wrap" role="status">
      <span className="c3-spin" aria-hidden="true" />
      {label && <span>{label}</span>}
    </span>
  );
}

// Inline message. tone: 'error' | 'warn' | 'success' | 'info'. Errors are announced to screen readers.
export function Notice({ tone = 'info', title, children, onRetry, onDismiss }) {
  return (
    <div className={`c3-notice c3-notice-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <div className="c3-notice-body">
        {title && <strong>{title}</strong>}
        {children && <div>{children}</div>}
      </div>
      {(onRetry || onDismiss) && (
        <div className="c3-notice-actions">
          {onRetry && (
            <button type="button" className="btn secondary c3-sm" onClick={onRetry}>
              Try again
            </button>
          )}
          {onDismiss && (
            <button type="button" className="btn-link-dark" onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// A part of the analysis that does not exist for this submission, with the reason. Never a placeholder result.
export function Unavailable({ title, reason }) {
  return (
    <section className="panel c3-unavailable" aria-label={title}>
      <h3 style={{ margin: '0 0 4px' }}>{title}</h3>
      <p className="muted" style={{ margin: 0 }}>{reason}</p>
    </section>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="panel c3-empty">
      <h3>{title}</h3>
      {children && <p className="muted">{children}</p>}
      {action}
    </div>
  );
}

// Modal dialog: focus moves in, Tab stays inside, Escape or the backdrop closes it, focus returns to the opener.
export function Dialog({ title, onClose, children, footer, wide = false }) {
  const ref = useRef(null);
  // Callers usually pass an inline onClose, which is a new function on every render. Keep the latest one in a ref so
  // the focus set-up below runs once per open: depending on onClose would re-run it on every keystroke and move
  // focus back to the first field while the user is typing in a later one.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const opener = document.activeElement;
    const node = ref.current;
    const focusables = () => node.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    (node.querySelector('[data-autofocus]') || focusables()[0] || node).focus();
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        closeRef.current();
      } else if (e.key === 'Tab') {
        const list = Array.from(focusables()).filter((el) => !el.disabled);
        if (list.length === 0) return;
        const first = list[0];
        const last = list[list.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (opener && opener.focus) opener.focus();
    };
  }, []);
  return (
    <div className="c3-backdrop" onMouseDown={(e) => e.target === e.currentTarget && closeRef.current()}>
      <div className={`c3-dialog${wide ? ' wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} ref={ref} tabIndex={-1}>
        <div className="c3-dialog-head">
          <h2>{title}</h2>
          <button type="button" className="btn-ghost c3-close" onClick={onClose} aria-label="Close">
            Close
          </button>
        </div>
        <div className="c3-dialog-body">{children}</div>
        {footer && <div className="c3-dialog-foot">{footer}</div>}
      </div>
    </div>
  );
}

// Replaces window.confirm for irreversible actions.
export function ConfirmDialog({ title, message, confirmLabel = 'Confirm', danger = false, busy = false, onConfirm, onCancel }) {
  return (
    <Dialog
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className="btn secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className={`btn${danger ? ' danger' : ''}`} onClick={onConfirm} disabled={busy} data-autofocus>
            {busy ? 'Working...' : confirmLabel}
          </button>
        </>
      }
    >
      <p style={{ margin: 0 }}>{message}</p>
    </Dialog>
  );
}

// Ordered progress through a workflow. steps: [{ key, label, disabled?, badge? }]
export function Stepper({ steps, current, onSelect }) {
  return (
    <nav aria-label="Marking steps">
      <ol className="c3-stepper">
        {steps.map((s, i) => (
          <li key={s.key} className={s.key === current ? 'on' : ''}>
            <button
              type="button"
              disabled={s.disabled}
              aria-current={s.key === current ? 'step' : undefined}
              onClick={() => onSelect(s.key)}
            >
              <span className="c3-step-num">{i + 1}</span>
              <span>{s.label}</span>
              {s.badge != null && <span className="c3-step-badge">{s.badge}</span>}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

// Plain-language explanation for common failures. Never shows stack traces or internal addresses.
export function friendlyError(err, fallback = 'Something went wrong. Please try again.') {
  if (!err) return fallback;
  if (err.status === 401) return 'Your session has expired. Please sign in again.';
  if (err.status === 403) return 'You do not have permission to do this.';
  if (err.status === 404) return 'We could not find that item.';
  if (err.status === 409) return err.message || 'This item has already been reviewed or finalized and cannot be changed.';
  if (err.status === 422) return 'Some details are not valid. Check the highlighted fields and try again.';
  if (err.status === 502 || err.status === 504) return 'The marking service is not responding right now. Please try again in a moment.';
  if (err.status === 503) return err.message || 'The result could not be saved. Please try again.';
  if (err.status >= 500) return fallback;
  return err.message || fallback;
}

// Where a submission comes from. The label is an inline badge next to the student id (queue and review page). It uses
// its own c3-source-badge class because the global .chip class is redefined by the login page as an absolutely
// positioned, animated decoration, which made this badge float over the page.
export function sourceKind(s) {
  if (!s) return 'student';
  if (s.provenance === 'test_fixture' || s.status === 'failed') return 'test';
  if (s.is_demo || s.provenance === 'pp1_demo') return 'sample';
  return 'student';
}
export const SOURCE_LABEL = { student: 'Student', sample: 'Sample', test: 'Test data' };

export function SourceBadge({ submission }) {
  const kind = sourceKind(submission);
  if (kind === 'student') return null;
  return <span className={`c3-source-badge ${kind}`} data-source={kind}>{SOURCE_LABEL[kind]}</span>;
}
