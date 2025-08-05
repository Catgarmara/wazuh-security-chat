'use client';

import * as React from 'react';
import { useChatStore } from '@/stores/chat';
import { useUIStore } from '@/stores/ui';
import { AIModel, ModelLoadRequest, ModelStatus } from '@/types';

interface ModelManagementState {
  loadingModels: Set<string>;
  unloadingModels: Set<string>;
  loadingProgress: Record<string, number>;
  modelErrors: Record<string, string>;
}

export function useModelManagement() {
  const { 
    availableModels, 
    loadedModels, 
    setLoadedModels, 
    setAvailableModels,
    updateModelStatus 
  } = useChatStore();
  const { addNotification } = useUIStore();
  
  const [state, setState] = React.useState<ModelManagementState>({
    loadingModels: new Set(),
    unloadingModels: new Set(),
    loadingProgress: {},
    modelErrors: {},
  });

  // Mock API endpoints - replace with actual backend calls
  const loadModel = React.useCallback(async (modelId: string, configuration?: Record<string, any>) => {
    try {
      setState(prev => ({
        ...prev,
        loadingModels: new Set([...prev.loadingModels, modelId]),
        loadingProgress: { ...prev.loadingProgress, [modelId]: 0 },
        modelErrors: { ...prev.modelErrors }
      }));

      addNotification({
        type: 'info',
        title: 'Loading Model',
        message: `Starting to load ${availableModels.find(m => m.id === modelId)?.display_name}...`,
      });

      // Simulate loading progress
      for (let progress = 10; progress <= 100; progress += 10) {
        await new Promise(resolve => setTimeout(resolve, 200));
        setState(prev => ({
          ...prev,
          loadingProgress: { ...prev.loadingProgress, [modelId]: progress }
        }));
      }

      // Update model status
      const model = availableModels.find(m => m.id === modelId);
      if (model) {
        const updatedModel: AIModel = {
          ...model,
          is_loaded: true,
          performance_metrics: {
            ...model.performance_metrics,
            tokens_per_second: Math.floor(Math.random() * 20) + 30,
            memory_usage: Math.floor(Math.random() * 2000000000) + 3000000000,
            response_time: Math.floor(Math.random() * 50) + 100,
          }
        };

        updateModelStatus(modelId, updatedModel);
        setLoadedModels([...loadedModels.filter(m => m.id !== modelId), updatedModel]);
      }

      addNotification({
        type: 'success',
        title: 'Model Loaded',
        message: `${model?.display_name} is now ready for use`,
      });

    } catch (error: any) {
      setState(prev => ({
        ...prev,
        modelErrors: { ...prev.modelErrors, [modelId]: error.message }
      }));

      addNotification({
        type: 'error',
        title: 'Loading Failed',
        message: `Failed to load model: ${error.message}`,
      });
    } finally {
      setState(prev => ({
        ...prev,
        loadingModels: new Set([...prev.loadingModels].filter(id => id !== modelId)),
        loadingProgress: { ...prev.loadingProgress }
      }));
    }
  }, [availableModels, loadedModels, updateModelStatus, setLoadedModels, addNotification]);

  const unloadModel = React.useCallback(async (modelId: string) => {
    try {
      setState(prev => ({
        ...prev,
        unloadingModels: new Set([...prev.unloadingModels, modelId])
      }));

      const model = loadedModels.find(m => m.id === modelId);
      addNotification({
        type: 'info',
        title: 'Unloading Model',
        message: `Freeing memory used by ${model?.display_name}...`,
      });

      // Simulate unloading delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Update model status
      updateModelStatus(modelId, { is_loaded: false });
      setLoadedModels(loadedModels.filter(m => m.id !== modelId));

      addNotification({
        type: 'success',
        title: 'Model Unloaded',
        message: `${model?.display_name} has been unloaded to save memory`,
      });

    } catch (error: any) {
      setState(prev => ({
        ...prev,
        modelErrors: { ...prev.modelErrors, [modelId]: error.message }
      }));

      addNotification({
        type: 'error',
        title: 'Unloading Failed',
        message: `Failed to unload model: ${error.message}`,
      });
    } finally {
      setState(prev => ({
        ...prev,
        unloadingModels: new Set([...prev.unloadingModels].filter(id => id !== modelId))
      }));
    }
  }, [loadedModels, updateModelStatus, setLoadedModels, addNotification]);

  const hotSwapModel = React.useCallback(async (fromModelId: string, toModelId: string) => {
    try {
      addNotification({
        type: 'info',
        title: 'Hot Swapping Models',
        message: 'Switching models without interrupting conversations...',
      });

      // Load new model first
      await loadModel(toModelId);
      
      // Then unload old model
      await unloadModel(fromModelId);

      addNotification({
        type: 'success',
        title: 'Hot Swap Complete',
        message: 'Models switched successfully',
      });

    } catch (error: any) {
      addNotification({
        type: 'error',
        title: 'Hot Swap Failed',
        message: `Model swap failed: ${error.message}`,
      });
    }
  }, [loadModel, unloadModel, addNotification]);

  const getModelMetrics = React.useCallback((modelId: string) => {
    const model = [...availableModels, ...loadedModels].find(m => m.id === modelId);
    return model?.performance_metrics;
  }, [availableModels, loadedModels]);

  const getTotalMemoryUsage = React.useCallback(() => {
    return loadedModels.reduce((total, model) => {
      return total + (model.performance_metrics?.memory_usage || 0);
    }, 0);
  }, [loadedModels]);

  const getLoadingProgress = React.useCallback((modelId: string) => {
    return state.loadingProgress[modelId] || 0;
  }, [state.loadingProgress]);

  const isModelLoading = React.useCallback((modelId: string) => {
    return state.loadingModels.has(modelId);
  }, [state.loadingModels]);

  const isModelUnloading = React.useCallback((modelId: string) => {
    return state.unloadingModels.has(modelId);
  }, [state.unloadingModels]);

  const getModelError = React.useCallback((modelId: string) => {
    return state.modelErrors[modelId];
  }, [state.modelErrors]);

  const clearModelError = React.useCallback((modelId: string) => {
    setState(prev => ({
      ...prev,
      modelErrors: { ...prev.modelErrors, [modelId]: '' }
    }));
  }, []);

  return {
    // Model operations
    loadModel,
    unloadModel,
    hotSwapModel,
    
    // State queries
    isModelLoading,
    isModelUnloading,
    getLoadingProgress,
    getModelMetrics,
    getTotalMemoryUsage,
    getModelError,
    clearModelError,
    
    // Model lists
    availableModels,
    loadedModels,
  };
}