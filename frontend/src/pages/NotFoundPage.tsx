import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section>
      <div className="page-intro">
        <h1>Page not found</h1>
        <p>
          The page you are looking for does not exist. <Link to="/">Back to all tools</Link>.
        </p>
      </div>
    </section>
  );
}
