"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="glass-panel panel-edge hidden rounded-[36px] p-8 lg:block">
          <div className="bg-grid rounded-[28px] border border-border/60 p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Finance trust layer</p>
            <h1 className="mt-4 max-w-xl text-5xl font-semibold leading-tight text-balance">
              A calmer operating system for the CEO dashboard.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
              Multi-tenant finance insights, org-scoped controls, and AI-ready reporting without changing your current backend model.
            </p>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                { icon: ShieldCheck, title: "Secure auth", text: "Bearer and cookie modes stay supported." },
                { icon: CheckCircle2, title: "RBAC-safe", text: "Owner, editor, and viewer experiences stay consistent." },
                { icon: Sparkles, title: "Executive UX", text: "Fast flows from data intake to narrative and reports." },
              ].map((item) => (
                <div key={item.title} className="rounded-[22px] border border-border/60 bg-card/70 p-4">
                  <item.icon className="h-5 w-5 text-primary" />
                  <p className="mt-4 font-medium">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="glass-panel panel-edge mx-auto w-full max-w-lg rounded-[32px] p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Welcome back</p>
          <h2 className="mt-3 text-3xl font-semibold">Sign in to AI COO</h2>
          <p className="mt-2 text-sm text-muted-foreground">Executive finance cockpit with org switching, insights, and reports.</p>
          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
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
            <Button className="w-full" disabled={login.isPending} type="submit">
              Sign in <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              New here?{" "}
              <Link className="text-primary underline-offset-4 hover:underline" href="/auth/register">
                Create account
              </Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
