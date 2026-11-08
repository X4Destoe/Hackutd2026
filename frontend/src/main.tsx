import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { UIProvider } from './shared/ui-store';
import { useEvents } from './shared/useEvents';
import './shared/tokens.css';
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 15000, retry: 1 } } });
function LiveEvents() { useEvents(); return null; }
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><UIProvider><LiveEvents/><App /></UIProvider></QueryClientProvider></React.StrictMode>);
