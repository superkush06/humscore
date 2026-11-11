import { Link } from "react-router";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-dvh flex-col px-3 gap-2">
        <h1 className="text-5xl md:text-7xl font-bold pb-4">404</h1>
        <p className="text-lg">
          <em>We hummed...</em> and couldn't find what you were looking for, sadly.
        </p>

        <p className="text-blue-500">
          <Link to="/">Back home</Link>
        </p>
    </div>
  );
}
