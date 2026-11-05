import React, { useEffect, useState } from "react";
import Head from "next/head";
import { LoginForm } from "@/components/LoginForm";
import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const savedToken = sessionStorage.getItem("auth_token");
    if (savedToken) {
      setToken(savedToken);
    }
    setIsReady(true);
  }, []);

  const handleLogout = () => {
    sessionStorage.removeItem("auth_token");
    setToken(null);
  };

  if (!isReady) {
    return null;
  }

  return (
    <>
      <Head>
        <title>Investment Rebalancer AI</title>
        <meta name="description" content="Automação determinística de rebalanceamento de carteiras" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        {!token ? (
          <LoginForm onSuccess={(newToken) => setToken(newToken)} />
        ) : (
          <Dashboard onLogout={handleLogout} />
        )}
      </main>
    </>
  );
}

