import { Link } from "react-router-dom";
import { tools } from "../tools";

export default function HomePage() {
  return (
    <section>
      <div className="page-intro">
        <h1>Every tool you need to work with PDFs</h1>
        <p>Pick a tool, upload your files, and download the result.</p>
      </div>
      {tools.length === 0 ? (
        <p className="empty-state">No tools are available yet.</p>
      ) : (
        <ul className="tool-grid">
          {tools.map((tool) => (
            <li key={tool.path}>
              <Link to={tool.path} className="tool-card">
                <h2>{tool.title}</h2>
                <p>{tool.description}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
