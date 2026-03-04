"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useRegister } from "@/features/auth/hooks";

export function RegisterForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const register = useRegister();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await register.mutateAsync({ email, password });
      router.replace("/auth/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <Card className="mx-auto mt-16 w-full max-w-md shadow-trust">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Start managing financial operations with AI COO.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={onSubmit}>
          <Input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input
            placeholder="Password (min 8 chars)"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          <Button className="w-full" disabled={register.isPending} type="submit">Create account</Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account? <a className="text-primary underline" href="/auth/login">Sign in</a>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
