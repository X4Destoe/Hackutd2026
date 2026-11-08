import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { UIProvider } from './shared/ui-store';
import './shared/tokens.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><UIProvider><App /></UIProvider></React.StrictMode>);
