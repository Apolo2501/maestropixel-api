  // prisma/seed.js
const { PrismaClient } = require("@prisma/client");
const bcrypt = require("bcrypt");

const prisma = new PrismaClient();

async function main() {
  const pwd2hashedPassword = await bcrypt.hash("V3ryS3cur3S3cr3tF0rN3xtAuth", 10);

  await prisma.user.create({
    data: {
      name: "Maestro Pixel",
      email: "anpol92@hotmail.com",
      hashedPassword: pwd2hashedPassword, // o hashedPassword si ya renombraste el campo
      lastLogin: new Date(),
    },
  });

  console.log("✅ Usuario creado con éxito");
}

main()
  .catch((e) => console.error("❌ Error al crear usuario:", e))
  .finally(() => prisma.$disconnect());