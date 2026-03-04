"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/features/auth/hooks";
import { bootstrapSession } from "@/lib/api/client";
import { useAppStore } from "@/store/appStore";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const setSession = useAppStore((s) => s.setSession);
  const login = useLogin();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login.mutateAsync({ email, password });
      const me = await bootstrapSession();
      setSession(me.user, me.orgs);
      router.replace(me.orgs.length ? "/app/dashboard" : "/app/orgs");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <Card className="mx-auto mt-16 w-full max-w-md shadow-trust">
      <CardHeader>
        <CardTitle>Welcome back</CardTitle>
        <CardDescription>Sign in to your AI COO workspace</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={onSubmit}>
          <Input aria-label="Email" placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input
            aria-label="Password"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          <Button className="w-full" disabled={login.isPending} type="submit">Sign in</Button>
          <p className="text-center text-sm text-muted-foreground">
            New here? <a className="text-primary underline" href="/auth/register">Create account</a>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
