from psycopg2 import sql as pgsql

from mcp.server.fastmcp import FastMCP

from mcp_server import db

mcp = FastMCP("football-analytics")

@mcp.tool()
def list_views() -> dict:
    """List the analytics views available to query, with a short description of each."""
    sql = """
        SELECT c.relname, obj_description(c.oid, 'pg_class')
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'analytics' AND c.relkind = 'v'
        ORDER BY c.relname
    """
    try:
        _, rows = db.fetch(sql)
        return {"views": [{"name": r[0], "description": r[1]} for r in rows]}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def describe_view(view_name: str) -> dict:
    """Show the columns and types of one analytics view. Text columns with a few
    distinct values also list those values, so use them instead of guessing.
    Call this before writing SQL."""
    sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'analytics' AND table_name = %s
        ORDER BY ordinal_position
    """
    try:
        _, rows = db.fetch(sql, (view_name,))
        if not rows:
            return {"error": f"No view named {view_name}. Call list_views first."}

        columns = []
        for name, data_type in rows:
            column = {"name": name, "type": data_type}
            if data_type in ("text", "character varying"):
                # sample the distinct values, keep them only if there are few
                sample = pgsql.SQL(
                    "SELECT DISTINCT {col} FROM {schema}.{view} "
                    "WHERE {col} IS NOT NULL LIMIT 11"
                ).format(
                    col=pgsql.Identifier(name),
                    schema=pgsql.Identifier("analytics"),
                    view=pgsql.Identifier(view_name),
                )
                _, values = db.fetch(sample)
                if len(values) <= 10:
                    column["values"] = [v[0] for v in values]
            columns.append(column)

        return {"view": view_name, "columns": columns}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def run_query(sql: str) -> dict:
    """Run one read-only SELECT query against the analytics views.
    Results are limited to 100 rows. Team names include 'FC', so use ILIKE."""
    try:
        return db.run_select(sql)
    except Exception as e:
        # return the error so the agent can fix its own SQL
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()