/**
 * UserMenu — shown in the extension header when the user is authenticated.
 * Displays the user's email initial, a dropdown with profile info and logout,
 * and a delete-account confirmation flow.
 */

import React, { useState, useRef, useEffect } from "react";
import type { UseAuthReturn } from "../hooks/useAuth";

interface UserMenuProps {
  auth: UseAuthReturn;
}

export const UserMenu: React.FC<UserMenuProps> = ({ auth }) => {
  const [open, setOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (!auth.user) return null;

  const initial = auth.user.email.charAt(0).toUpperCase();

  const handleLogout = async () => {
    setOpen(false);
    await auth.logout();
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await auth.deleteAccount();
    } catch {
      // error displayed via auth.error in parent
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
      setOpen(false);
    }
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* Avatar button */}
      <button
        id="user-menu-button"
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="true"
        title={auth.user.email}
        className="w-7 h-7 rounded-full bg-brand flex items-center justify-center text-xs font-bold text-white hover:bg-brand-hover transition-colors focus:outline-none focus:ring-2 focus:ring-brand/40 focus:ring-offset-1"
      >
        {initial}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-9 w-60 bg-surface border border-theme rounded-xl shadow-xl z-50 overflow-hidden text-primary animate-in fade-in zoom-in-95 duration-150"
          role="menu"
        >
          {/* Profile info */}
          <div className="px-4 py-3 border-b border-theme bg-elevated/40">
            <div className="flex items-center justify-between">
              <p className="text-[11px] text-muted">Signed in as</p>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-brand/10 text-brand border border-brand/20">
                Active
              </span>
            </div>
            <p
              className="text-xs font-semibold text-primary truncate mt-0.5"
              title={auth.user.email}
            >
              {auth.user.email}
            </p>
          </div>

          {!showDeleteConfirm ? (
            <div className="py-1">
              {/* Logout */}
              <button
                id="user-menu-logout"
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-xs text-secondary hover:text-primary hover:bg-elevated transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-3.5 h-3.5 text-muted"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
                Sign out
              </button>

              {/* Delete account */}
              <button
                id="user-menu-delete"
                type="button"
                role="menuitem"
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full text-left px-4 py-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors border-t border-theme flex items-center gap-2"
              >
                <svg
                  className="w-3.5 h-3.5 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Delete account
              </button>
            </div>
          ) : (
            /* Confirmation panel */
            <div className="px-4 py-3 space-y-2.5">
              <p className="text-[11px] text-secondary leading-relaxed">
                Permanently delete your account and all its conversations? This cannot be
                undone.
              </p>
              <div className="flex space-x-2">
                <button
                  id="user-menu-delete-confirm"
                  type="button"
                  disabled={isDeleting}
                  onClick={handleDeleteAccount}
                  className="flex-1 py-1.5 rounded-lg text-[11px] font-semibold bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white transition-colors"
                >
                  {isDeleting ? "Deleting…" : "Yes, delete"}
                </button>
                <button
                  id="user-menu-delete-cancel"
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-1.5 rounded-lg text-[11px] font-medium bg-elevated hover:bg-surface border border-theme text-secondary hover:text-primary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
