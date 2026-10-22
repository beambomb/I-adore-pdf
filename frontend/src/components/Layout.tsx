import { Link, NavLink, Outlet } from "react-router-dom";
import { tools } from "../tools";

export default function Layout() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <Link to="/" className="app-brand">
            I-adore-<span>pdf</span>
          </Link>
          <nav aria-label="Tools" className="app-nav">
            {tools.map((tool) => (
              <NavLink key={tool.path} to={tool.path} className="app-nav__link">
                {tool.title}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <div className="app-footer__inner">Files are deleted automatically after processing.</div>
      </footer>
    </div>
  );
}
