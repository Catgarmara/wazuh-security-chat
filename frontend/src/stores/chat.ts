import { create } from 'zustand';
import { ChatSession, ChatMessage, AIModel } from '@/types';
import { createLogger } from '@/lib/utils';

const logger = createLogger('chat-store');

interface ChatState {
  sessions: ChatSession[];
  messages: Record<string, ChatMessage[]>; // sessionId -> messages
  activeSession: string | null;
  availableModels: AIModel[];
  loadedModels: AIModel[];
  isTyping: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  createSession: () => ChatSession;
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void;
  removeSession: (sessionId: string) => void;
  setActiveSession: (sessionId: string | null) => void;
  
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => void;
  removeMessage: (sessionId: string, messageId: string) => void;
  
  setAvailableModels: (models: AIModel[]) => void;
  setLoadedModels: (models: AIModel[]) => void;
  updateModelStatus: (modelId: string, updates: Partial<AIModel>) => void;
  
  setTyping: (isTyping: boolean) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Computed
  getSessionMessages: (sessionId: string) => ChatMessage[];
  getActiveSessionMessages: () => ChatMessage[];
  getModelById: (modelId: string) => AIModel | undefined;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  messages: {},
  activeSession: null,
  availableModels: [],
  loadedModels: [],
  isTyping: false,
  isLoading: false,
  error: null,

  setSessions: (sessions) => {
    logger.debug('Setting sessions:', sessions.length);
    set({ sessions });
  },

  addSession: (session) => {
    logger.info('Adding session:', session.id);
    set((state) => ({
      sessions: [session, ...state.sessions],
      messages: { ...state.messages, [session.id]: [] },
    }));
  },

  createSession: () => {
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      model_id: null,
      system_prompt: null,
      metadata: {},
    };
    
    logger.info('Creating new session:', newSession.id);
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      messages: { ...state.messages, [newSession.id]: [] },
      activeSession: newSession.id,
    }));
    
    return newSession;
  },

  updateSession: (sessionId, updates) => {
    logger.debug('Updating session:', sessionId);
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, ...updates } : s
      ),
    }));
  },

  removeSession: (sessionId) => {
    logger.info('Removing session:', sessionId);
    set((state) => {
      const newMessages = { ...state.messages };
      delete newMessages[sessionId];
      
      return {
        sessions: state.sessions.filter((s) => s.id !== sessionId),
        messages: newMessages,
        activeSession: state.activeSession === sessionId ? null : state.activeSession,
      };
    });
  },

  setActiveSession: (sessionId) => {
    if (sessionId !== get().activeSession) {
      logger.debug('Setting active session:', sessionId);
      set({ activeSession: sessionId });
    }
  },

  setMessages: (sessionId, messages) => {
    logger.debug('Setting messages for session:', sessionId, messages.length);
    set((state) => ({
      messages: { ...state.messages, [sessionId]: messages },
    }));
  },

  addMessage: (sessionId, message) => {
    logger.debug('Adding message to session:', sessionId);
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] || []), message],
      },
    }));
  },

  updateMessage: (sessionId, messageId, updates) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: (state.messages[sessionId] || []).map((m) =>
          m.id === messageId ? { ...m, ...updates } : m
        ),
      },
    }));
  },

  removeMessage: (sessionId, messageId) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: (state.messages[sessionId] || []).filter((m) => m.id !== messageId),
      },
    }));
  },

  setAvailableModels: (models) => {
    logger.debug('Setting available models:', models.length);
    set({ availableModels: models });
  },

  setLoadedModels: (models) => {
    logger.debug('Setting loaded models:', models.length);
    set({ loadedModels: models });
  },

  updateModelStatus: (modelId, updates) => {
    set((state) => ({
      availableModels: state.availableModels.map((m) =>
        m.id === modelId ? { ...m, ...updates } : m
      ),
      loadedModels: state.loadedModels.map((m) =>
        m.id === modelId ? { ...m, ...updates } : m
      ),
    }));
  },

  setTyping: (isTyping) => {
    set({ isTyping });
  },

  setLoading: (isLoading) => {
    set({ isLoading });
  },

  setError: (error) => {
    if (error) {
      logger.error('Chat error:', error);
    }
    set({ error });
  },

  // Computed getters
  getSessionMessages: (sessionId) => {
    return get().messages[sessionId] || [];
  },

  getActiveSessionMessages: () => {
    const { activeSession, messages } = get();
    return activeSession ? messages[activeSession] || [] : [];
  },

  getModelById: (modelId) => {
    const { availableModels } = get();
    return availableModels.find((model) => model.id === modelId);
  },
}));