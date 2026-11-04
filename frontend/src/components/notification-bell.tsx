"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { EASE } from "@/components/motion";
import { useAuth } from "@/components/providers";
import { api, type InboxItem } from "@/lib/api";

const POLL_MS = 25_000;

export function timeAgo(iso: string) {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/** Internal links stay in the app; admin links (staff alerts) open the Django admin. */
export function isInternal(link: string) {
  return link.startsWith("/") && !link.startsWith("/admin");
}

export function useInbox(enabled: boolean) {
  const queryClient = useQueryClient();
  const unread = useQuery({
    queryKey: ["inbox", "unread"],
    queryFn: api.unreadCount,
    enabled,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: false,
  });
  const markRead = async (body: { ids: number[] } | { all: true }) => {
    const result = await api.markRead(body);
    queryClient.setQueryData(["inbox", "unread"], result);
    await queryClient.invalidateQueries({ queryKey: ["inbox", "list"] });
  };
  return { unread: unread.data?.unread_count ?? 0, markRead };
}

export function NotificationBell() {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const { unread, markRead } = useInbox(Boolean(user));
  const list = useQuery({
    queryKey: ["inbox", "list", 1],
    queryFn: () => api.inbox(1, 8),
    enabled: Boolean(user) && open,
  });

  // When something new arrives while the page is open, say so once.
  const previous = useRef<number | null>(null);
  useEffect(() => {
    if (!user) return;
    if (previous.current !== null && unread > previous.current) {
      api
        .inbox(1, 1)
        .then((latest) => {
          const item = latest.results[0];
          if (item && !item.read_at)
            toast(item.title, { description: item.body });
        })
        .catch(() => undefined);
    }
    previous.current = unread;
  }, [unread, user]);

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (panel.current && !panel.current.contains(event.target as Node))
        setOpen(false);
    };
    const esc = (event: KeyboardEvent) =>
      event.key === "Escape" && setOpen(false);
    window.addEventListener("pointerdown", close);
    window.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);

  if (!user) return null;

  const openItem = async (item: InboxItem) => {
    setOpen(false);
    if (!item.read_at)
      await markRead({ ids: [item.id] }).catch(() => undefined);
    if (isInternal(item.link)) router.push(item.link);
    else if (item.link) window.open(item.link, "_blank", "noopener");
  };

  return (
    <div className="bell" ref={panel}>
      <button
        type="button"
        className="bell-button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={
          unread ? `Notifications, ${unread} unread` : "Notifications"
        }
      >
        <Bell size={17} strokeWidth={1.6} />
        <AnimatePresence>
          {unread > 0 && (
            <motion.span
              key={unread}
              className="bell-badge tabular"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 20 }}
            >
              {unread > 9 ? "9+" : unread}
            </motion.span>
          )}
        </AnimatePresence>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="bell-panel"
            role="dialog"
            aria-label="Notifications"
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.35, ease: EASE }}
            data-lenis-prevent
          >
            <header>
              <strong>Updates</strong>
              {unread > 0 && (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => markRead({ all: true })}
                >
                  Mark all read
                </button>
              )}
            </header>
            {list.isLoading ? (
              <p className="bell-empty">Loading…</p>
            ) : !list.data?.results.length ? (
              <p className="bell-empty">
                Nothing yet. We&apos;ll let you know here when your order moves
                along.
              </p>
            ) : (
              <ul>
                {list.data.results.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={item.read_at ? "" : "is-unread"}
                      onClick={() => openItem(item)}
                    >
                      <span className="bell-dot" aria-hidden="true" />
                      <span>
                        <strong>{item.title}</strong>
                        <span>{item.body}</span>
                        <small>{timeAgo(item.created_at)}</small>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <footer>
              <Link
                href="/account?tab=notifications"
                onClick={() => setOpen(false)}
                className="text-link"
              >
                All updates
              </Link>
            </footer>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
