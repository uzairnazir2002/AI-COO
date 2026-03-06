"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, LineChart, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAcceptInvite, useRegister } from "@/features/auth/hooks";

export function RegisterForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const register = useRegister();
  const acceptInvite = useAcceptInvite();
  const inviteMode = inviteToken.length > 0;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setInviteToken(params.get("invite_token") || "");
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (inviteMode) {
        await acceptInvite.mutateAsync({ token: inviteToken, password });
        router.replace("/auth/login");
        return;
      }
      await register.mutateAsync({ email, password });
      router.replace(`/auth/confirm?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : inviteMode ? "Invite acceptance failed" : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="glass-panel panel-edge mx-auto w-full max-w-lg rounded-[32px] p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">{inviteMode ? "Accept invite" : "Create account"}</p>
          <h1 className="mt-3 text-3xl font-semibold">{inviteMode ? "Join your organization" : "Start your workspace"}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {inviteMode
              ? "Set your password to accept the invitation and activate access."
              : "Register first, then confirm your account and create your first organization inside the app."}
          </p>
          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
            {!inviteMode ? (
              <Input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            ) : (
              <Input value={inviteToken} readOnly aria-label="Invite token" />
            )}
            <Input
              placeholder="Password (min 8 chars)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
            {error ? <p className="text-sm text-danger">{error}</p> : null}
            <Button className="w-full" disabled={register.isPending || acceptInvite.isPending} type="submit">
              {inviteMode ? "Accept invite" : "Create account"} <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              {inviteMode ? "Already set up?" : "Already have an account?"}{" "}
              <Link className="text-primary underline-offset-4 hover:underline" href="/auth/login">
                Sign in
              </Link>
            </p>
          </form>
        </section>

        <section className="glass-panel panel-edge hidden rounded-[36px] p-8 lg:block">
          <div className="bg-grid rounded-[28px] border border-border/60 p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">{inviteMode ? "Invitation flow" : "Onboarding flow"}</p>
            <h2 className="mt-4 max-w-xl text-5xl font-semibold leading-tight text-balance">
              {inviteMode ? "Accept the invite. Join the workspace. Start contributing." : "Register. Confirm access. Start seeing signal."}
            </h2>
            <div className="mt-10 space-y-4">
              {[
                { icon: Building2, title: inviteMode ? "Join org" : "Create org", text: inviteMode ? "The token links you directly to the invited workspace." : "First-time users are routed into the org creation and onboarding workspace." },
                { icon: LineChart, title: inviteMode ? "Load data" : "Confirm account", text: inviteMode ? "Once inside, manual entry and CSV import remain fully backed by current endpoints." : "Registration now routes through the confirmation flow that matches the backend." },
                { icon: Users, title: "Scale access", text: "Owner, editor, and viewer permissions stay aligned with backend enforcement." },
              ].map((item) => (
                <div key={item.title} className="flex gap-4 rounded-[22px] border border-border/60 bg-card/70 p-4">
                  <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                    <item.icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
