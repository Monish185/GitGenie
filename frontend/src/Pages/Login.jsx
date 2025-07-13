import React, { useState } from 'react';
import axios from 'axios';

function Login() {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async () => {
        setIsLoading(true);
        setError('');
        
        try {
            const res = await axios.get(`${import.meta.env.VITE_BACKEND_URL}/auth/login`, {
                timeout: 10000, // 10 second timeout
            });
            
            const data = res.data;
            
            if (data?.authorization_url) {
                // Validate URL before redirecting
                try {
                    new URL(data.authorization_url);
                    window.location.href = data.authorization_url;
                } catch (urlError) {
                    throw new Error('Invalid authorization URL received');
                }
            } else {
                throw new Error('No authorization URL received from server');
            }
        } catch (error) {
            console.error('Login failed:', error);
            
            // User-friendly error messages
            if (error.code === 'ECONNABORTED') {
                setError('Connection timeout. Please try again.');
            } else if (error.response?.status === 500) {
                setError('Server error. Please try again later.');
            } else if (error.response?.status === 404) {
                setError('Authentication service not found.');
            } else if (error.message.includes('Network Error')) {
                setError('Network error. Please check your connection.');
            } else {
                setError(error.message || 'Login failed. Please try again.');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handleLogin();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4">
            <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
                <div className="text-center mb-6">
                    <h1 className="text-2xl font-bold text-gray-800 mb-2">Welcome Back</h1>
                    <p className="text-gray-600">Sign in to your account</p>
                </div>

                {error && (
                    <div 
                        className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md"
                        role="alert"
                        aria-live="polite"
                    >
                        <p className="text-red-700 text-sm">{error}</p>
                    </div>
                )}

                <button
                    onClick={handleLogin}
                    onKeyPress={handleKeyPress}
                    disabled={isLoading}
                    className={`
                        w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg font-medium
                        transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                        ${isLoading 
                            ? 'bg-gray-400 cursor-not-allowed' 
                            : 'bg-gray-900 hover:bg-gray-800 active:bg-gray-900'
                        }
                        text-white
                    `}
                    aria-label="Sign in with GitHub"
                >
                    {isLoading ? (
                        <>
                            <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span>Signing in...</span>
                        </>
                    ) : (
                        <>
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                                <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd"></path>
                            </svg>
                            <span>Continue with GitHub</span>
                        </>
                    )}
                </button>

                <p className="mt-4 text-xs text-gray-500 text-center">
                    By signing in, you agree to our Terms of Service and Privacy Policy.
                </p>
            </div>
        </div>
    );
}

export default Login;