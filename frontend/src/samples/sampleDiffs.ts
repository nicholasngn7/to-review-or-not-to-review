/**
 * Realistic but fake sample diffs for demoing MR Review Council without a real
 * merge request. All content is generic and invented — no proprietary code.
 */

import type { ReviewerPersona } from "../types/review";

export interface SampleDiff {
  id: string;
  label: string;
  title: string;
  description: string;
  diffText: string;
  recommendedPersonas: ReviewerPersona[];
}

// 1) Low-risk frontend change with a matching test update.
const LOW_RISK_FRONTEND = `diff --git a/src/components/Counter.tsx b/src/components/Counter.tsx
--- a/src/components/Counter.tsx
+++ b/src/components/Counter.tsx
@@ -1,8 +1,9 @@
 import { useState } from "react";

 export function Counter() {
   const [count, setCount] = useState(0);
-  const increment = () => setCount(count + 1);
+  const increment = () => setCount((c) => c + 1);
+  const reset = () => setCount(0);
   return (
     <div>
       <span>{count}</span>
diff --git a/src/components/Counter.test.tsx b/src/components/Counter.test.tsx
--- a/src/components/Counter.test.tsx
+++ b/src/components/Counter.test.tsx
@@ -9,4 +9,10 @@ describe("Counter", () => {
     expect(screen.getByText("1")).toBeInTheDocument();
   });

+  it("resets the count", () => {
+    render(<Counter />);
+    fireEvent.click(screen.getByText("Reset"));
+    expect(screen.getByText("0")).toBeInTheDocument();
+  });
+
 });
`;

// 2) Higher-risk backend/auth change with several real risk indicators and no
//    matching test update.
const RISKY_BACKEND_AUTH = `diff --git a/backend/app/api/auth.py b/backend/app/api/auth.py
--- a/backend/app/api/auth.py
+++ b/backend/app/api/auth.py
@@ -1,6 +1,22 @@
 import os
-import logging
+import subprocess
+import requests
 from fastapi import APIRouter

 router = APIRouter()
-logger = logging.getLogger(__name__)
+
+API_TOKEN = "sk_live_51H8xExampleToken"  # TODO: move to secret manager
+
+
+@router.post("/login")
+def login(payload: dict):
+    user = payload["username"]
+    cmd = "id " + user
+    subprocess.run(cmd, shell=True)
+    rule = eval(payload.get("rule", "True"))
+    resp = requests.get("http://auth.internal/validate?u=" + user)
+    try:
+        token = resp.json()["token"]
+    except Exception:
+        pass
+    return {"token": API_TOKEN, "ok": rule}
`;

// 3) Mixed full-stack change touching frontend, backend, config, and docs.
const MIXED_FULLSTACK = `diff --git a/src/components/Banner.tsx b/src/components/Banner.tsx
--- a/src/components/Banner.tsx
+++ b/src/components/Banner.tsx
@@ -1,7 +1,8 @@
 export function Banner() {
   return (
-    <div className="banner">
-      <span>Welcome</span>
+    <div className="banner" title="Welcome banner">
+      <span>Welcome to the new dashboard</span>
+      {/* TODO: localize this label */}
     </div>
   );
 }
diff --git a/backend/app/config.py b/backend/app/config.py
--- a/backend/app/config.py
+++ b/backend/app/config.py
@@ -1,3 +1,5 @@
 import os

 DEBUG = os.getenv("DEBUG", "false")
+# TODO: validate required settings on startup
+FEATURE_DASHBOARD = os.getenv("FEATURE_DASHBOARD", "true")
diff --git a/config/app.yaml b/config/app.yaml
--- a/config/app.yaml
+++ b/config/app.yaml
@@ -1,3 +1,4 @@
 service:
   name: mr-review
   port: 8000
+  feature_dashboard: true
diff --git a/docs/usage.md b/docs/usage.md
--- a/docs/usage.md
+++ b/docs/usage.md
@@ -1,3 +1,5 @@
 # Usage

 Run the app locally.
+
+The dashboard feature is now enabled by default.
`;

export const SAMPLE_DIFFS: SampleDiff[] = [
  {
    id: "low-risk-frontend",
    label: "Low-risk frontend change",
    title: "Add reset button to Counter",
    description:
      "Small React component tweak with a matching test update. Expect a mostly clean review.",
    diffText: LOW_RISK_FRONTEND,
    recommendedPersonas: ["architect", "qa", "frontend"],
  },
  {
    id: "risky-backend-auth",
    label: "Risky backend auth change",
    title: "Add login handler to auth service",
    description:
      "Python auth endpoint with secret handling, eval/subprocess usage, a swallowed exception, and no tests.",
    diffText: RISKY_BACKEND_AUTH,
    recommendedPersonas: ["security", "qa", "backend", "sre"],
  },
  {
    id: "mixed-fullstack",
    label: "Mixed full-stack change",
    title: "Enable dashboard feature across the stack",
    description:
      "Touches frontend, backend, config, and docs in one MR. Expect scope/maintainability feedback.",
    diffText: MIXED_FULLSTACK,
    recommendedPersonas: ["architect", "qa", "frontend", "backend", "product"],
  },
];
