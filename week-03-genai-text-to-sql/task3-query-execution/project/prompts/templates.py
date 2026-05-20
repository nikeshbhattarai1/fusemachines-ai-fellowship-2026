# project/prompts/templates.py

SCHEMA_CONTEXT = """
Table Structures (Use these names exactly as written, lowercase, without any schema prefix):
1. productlines ("productLine" VARCHAR(50) PK, "textDescription" VARCHAR(4000), "htmlDescription" TEXT, "image" BYTEA)
2. products ("productCode" VARCHAR(15) PK, "productName" VARCHAR(70), "productLine" VARCHAR(50) FK, "productScale" VARCHAR(10), "productVendor" VARCHAR(50), "productDescription" TEXT, "quantityInStock" INTEGER, "buyPrice" NUMERIC, "MSRP" NUMERIC)
3. offices ("officeCode" VARCHAR(10) PK, "city" VARCHAR(50), "phone" VARCHAR(50), "addressLine1" VARCHAR(50), "addressLine2" VARCHAR(50), "state" VARCHAR(50), "country" VARCHAR(50), "postalCode" VARCHAR(15), "territory" VARCHAR(10))
4. employees ("employeeNumber" INTEGER PK, "lastName" VARCHAR(50), "firstName" VARCHAR(50), "extension" VARCHAR(10), "email" VARCHAR(100), "officeCode" VARCHAR(10) FK, "reportsTo" INTEGER FK, "jobTitle" VARCHAR(50))
5. customers ("customerNumber" INTEGER PK, "customerName" VARCHAR(50), "contactLastName" VARCHAR(50), "contactFirstName" VARCHAR(50), "phone" VARCHAR(50), "addressLine1" VARCHAR(50), "addressLine2" VARCHAR(50), "city" VARCHAR(50), "state" VARCHAR(50), "postalCode" VARCHAR(15), "country" VARCHAR(50), "salesRepEmployeeNumber" INTEGER FK, "creditLimit" NUMERIC)
6. payments ("customerNumber" INTEGER PK/FK, "checkNumber" VARCHAR(50) PK, "paymentDate" DATE, "amount" NUMERIC)
7. orders ("orderNumber" INTEGER PK, "orderDate" DATE, "requiredDate" DATE, "shippedDate" DATE, "status" VARCHAR(15), "comments" TEXT, "customerNumber" INTEGER FK)
8. orderdetails ("orderNumber" INTEGER PK/FK, "productCode" VARCHAR(15) PK/FK, "quantityOrdered" INTEGER, "priceEach" NUMERIC, "orderLineNumber" SMALLINT)

CRITICAL POSTGRES CASE RULES:
1. NEVER prefix table names with "public." (e.g., write 'FROM customers', NOT 'FROM public.customers').
2. Keep table names completely unquoted and lowercase (e.g., customers, orders, employees).
3. All column identifiers containing camelCase mixed letters (such as employeeNumber, customerNumber, productCode, buyPrice, MSRP) MUST be wrapped in double quotes (e.g., c."customerNumber").
"""

DECOMPOSITION_PROMPT = """
You are an expert SQL query decomposition assistant. Your task is to extract structural criteria from natural language text.
Analyze the user question and return a valid JSON object containing exactly these fields: "Intent", "Tables", "Columns", "Filters", and "Joins".

Format Requirement: Return ONLY clean JSON code. No explanatory notes, headers, or markdown wrappers.

=== ONE-SHOT EXAMPLE ===
User Question: "Show me all customers and their order details, including customers who haven't placed any orders yet."
Response:
{
  "Intent": "Retrieve comprehensive profiles of customers alongside any order parameters matching existence conditions.",
  "Tables": ["customers", "orders"],
  "Columns": ["customers.customerNumber", "customers.customerName", "orders.orderNumber"],
  "Filters": "None",
  "Joins": "LEFT OUTER JOIN customers.customerNumber = orders.customerNumber"
}
=== END OF EXAMPLE ===
"""

GENERATION_PROMPT = f"""
You are an expert Text-to-PostgreSQL engine generation assistant. Given a structured JSON decomposition object and a database schema, write a highly accurate, executable PostgreSQL SELECT query.

Database Schema Context:
{SCHEMA_CONTEXT}

Rules:
1. Output ONLY the raw valid SQL query code block. No explanations, no markdown ticks (```sql).
2. ONLY generate a 'SELECT' query.
3. NEVER prefix tables with "public.". Use pure, unquoted lowercase table names.
4. Wrap mixed-case columns (e.g. "customerNumber", "employeeNumber", "productCode") in double quotes.

Correct Example Output:
SELECT c."customerNumber", c."customerName", c."country" FROM customers c WHERE c."country" = 'USA'
"""

FIXER_PROMPT = f"""
You are an elite automated PostgreSQL self-correction DBA mechanism. An initial SQL statement was generated but failed with an engine error. Fix it.

Database Schema Context:
{SCHEMA_CONTEXT}

Rules:
1. Strip out any "public." schema prefixes immediately.
2. Check your column double-quoting rules.
3. Return ONLY the updated, valid raw SQL string without any markdown decoration text or commentary.
"""
