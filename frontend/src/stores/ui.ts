import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UIState, Notification } from '@/types';
import { generateId, createLogger } from '@/lib/utils';

const logger = createLogger('ui-store');

interface UIStore extends UIState {
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveSession: (sessionId: string | undefined) => void;
  setSelectedModel: (modelId: string | undefined) => void;
  setViewMode: (mode: 'chat' | 'dashboard' | 'settings') => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      theme: 'system',
      sidebar_collapsed: false,
      active_session: undefined,
      selected_model: undefined,
      view_mode: 'chat',
      notifications: [],

      setTheme: (theme) => {
        logger.debug('Setting theme:', theme);
        set({ theme });
      },

      toggleSidebar: () => {
        const collapsed = !get().sidebar_collapsed;
        logger.debug('Toggling sidebar:', collapsed);
        set({ sidebar_collapsed: collapsed });
      },

      setSidebarCollapsed: (collapsed) => {
        logger.debug('Setting sidebar collapsed:', collapsed);
        set({ sidebar_collapsed: collapsed });
      },

      setActiveSession: (sessionId) => {
        if (sessionId !== get().active_session) {
          logger.debug('Setting active session:', sessionId);
          set({ active_session: sessionId });
        }
      },

      setSelectedModel: (modelId) => {
        if (modelId !== get().selected_model) {
          logger.debug('Setting selected model:', modelId);
          set({ selected_model: modelId });
        }
      },

      setViewMode: (mode) => {
        logger.debug('Setting view mode:', mode);
        set({ view_mode: mode });
      },

      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: generateId(),
          timestamp: new Date().toISOString(),
          read: false,
        };
        
        logger.info('Adding notification:', newNotification.title);
        
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50), // Keep only last 50
        }));
      },

      markNotificationRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        }));
      },

      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      },

      clearNotifications: () => {
        logger.debug('Clearing all notifications');
        set({ notifications: [] });
      },
    }),
    {
      name: 'wazuh-ai-ui',
      partialize: (state) => ({
        theme: state.theme,
        sidebar_collapsed: state.sidebar_collapsed,
        view_mode: state.view_mode,
        selected_model: state.selected_model,
      }),
    }
  )
);