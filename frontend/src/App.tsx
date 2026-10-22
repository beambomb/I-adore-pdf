import { useEffect, useState } from "react";

type Status = "checking" | "ok" | "down";

export default function App() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? setStatus("ok") : setStatus("down")))
      .catch(() => setStatus("down"));
  }, []);

  return (
    <main>
      <h1>I-adore-pdf</h1>
      <p>
        Backend status:{" "}
        <strong>{status === "checking" ? "Checking..." : status === "ok" ? "OK" : "Unavailable"}</strong>
      </p>
    </main>
  );
}
