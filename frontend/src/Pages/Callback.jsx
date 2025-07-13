import axios from 'axios';
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Callback() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const hasfetched = useRef(false);

    useEffect(() => {
  const fetchToken = async () => {
    if (hasfetched.current) return;
    hasfetched.current = true;

    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
   
    
    if (!code) {
      console.log("No code found, skipping token fetch.");
      return;  
    }

    try {
      const res = await axios.get(`${import.meta.env.VITE_BACKEND_URL}/auth/callback?code=${code}`);
      

      const token = res.data?.access_token;
      if (!token) throw new Error("No access token received");

      localStorage.setItem("access_token", token);
      console.log("Access token stored successfully");

      
      window.history.replaceState({}, document.title, "/repos");
      navigate("/repos");
    } catch (error) {
      console.error("Callback failed:", error);
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  fetchToken();
}, []);


    return ( 
        <>
        <div className='flex flex-col items-center justify-center h-screen bg-gray-100'>
            {loading ? (
                <p className='text-blue-500'>Loading...</p>
            ) : (
                <p className='text-green-500'>Login successful! Redirecting...</p>
            )}
        </div>
        </>
     );
}

export default Callback;