**Why is .env better than writing passwords in code?**
-> Storing secrets such as database passwords directly in source code is risky. Anyone who can access the code or its git history may be able to see and steal those credentials. A .env file helps avoid this problem by keeping sensitive information outside the codebase. It also makes it easier to use different values for development, testing, and production without changing the code itself. When a credential needs to be updated, you only change the .env file. You do not change the application code.

**Why is treating the database as a separate service useful?**
-> Treating the database as a separate service means it is not tightly tied to the application. Both can be scaled, replaced or restarted on their own. If the database goes down, the API container keeps running and can reconnect when the database is back. It also makes it easy to switch from PostgreSQL to another database like MySQL by only changing the connection string without changing the code.

**Why does Docker make development and production similar?**
-> Docker puts PostgreSQL and its system libraries and setup scripts into one container. That container runs the same way on a developer’s laptop and on a cloud server. This removes the common "works on my machine" problem. Everyone on the team and all deployment systems use the same environment. So any bug found locally is the same bug that would appear in production.

