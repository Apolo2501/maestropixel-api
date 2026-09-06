import "dotenv/config"; // 👈 esto carga el .env antes de usar env()
import { defineConfig, env } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  datasource: {
    url: process.env.DATABASE_URL!,
    // url: env("DATABASE_URL"),
  },
});
