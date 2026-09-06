import axios from "axios";
import { XMLParser } from "fast-xml-parser";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const SOAP_URL = "https://servayto.madrid.es/MTPAR_WSINFO/InfoParking";

const BODY = `<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:tem="http://tempuri.org/">
   <soapenv:Header/>
   <soapenv:Body>
      <tem:GetListParking>
         <tem:language>ES</tem:language>
      </tem:GetListParking>
   </soapenv:Body>
</soapenv:Envelope>
`;

async function ingest() {
  console.log("📡 Llamando al SOAP del Ayuntamiento...");

  const response = await axios.post(SOAP_URL, BODY, {
    headers: {
      "Content-Type": "text/xml;charset=UTF-8",
      SOAPAction: "http://tempuri.org/iInfoParking/GetListParking",
    },
  });

  const parser = new XMLParser({ ignoreAttributes: false });
  const xml = parser.parse(response.data);

  const envelope = xml["soap:Envelope"];
  const body = envelope["soap:Body"];
  const responseNode = body.GetListParkingResponse;
  const result = responseNode.GetListParkingResult;

  const array = result["ns2:ArrayOflstParking"];
  const list = array["ns2:lstParking"];

  console.log(`✔ lstParking encontrado: ${list.length} elementos`);

  // for (const p of list) {
  //   // --- Validación de ID ---
  //   const pid = Number(p.id);

  //   if (!pid || Number.isNaN(pid)) {
  //     console.warn("⚠ Parking sin ID válido, se omite:", p);
  //     continue;
  //   }

  //   // --- Validación de coordenadas ---
  //   const lat = Number(p.latitude);
  //   const lon = Number(p.longitude);

  //   if (Number.isNaN(lat) || Number.isNaN(lon)) {
  //     console.warn(`⚠ Parking ${pid} sin coordenadas válidas, se omite`);
  //     continue;
  //   }

  //   // --- Limpieza de campos opcionales ---
  //   const safe = (v: any) => (v === undefined || v === null ? null : v);

  //   await prisma.parking.upsert({
  //     where: { id: pid },
  //     update: {
  //       name: safe(p.name),
  //       nickName: safe(p.nickName),
  //       address: safe(p.address),
  //       town: safe(p.town),
  //       state: safe(p.state),
  //       areaCode: safe(p.areaCode),
  //       latitude: lat,
  //       longitude: lon,
  //       category: safe(p.category),
  //       familyCode: safe(p.familyCode),
  //       type: safe(p.type),
  //     },
  //     create: {
  //       id: pid,
  //       name: safe(p.name),
  //       nickName: safe(p.nickName),
  //       address: safe(p.address),
  //       town: safe(p.town),
  //       state: safe(p.state),
  //       areaCode: safe(p.areaCode),
  //       latitude: lat,
  //       longitude: lon,
  //       category: safe(p.category),
  //       familyCode: safe(p.familyCode),
  //       type: safe(p.type),
  //     },
  //   });

  //   // --- Ocupación ---
  //   if (p.lstOccupation?.occupation) {
  //     const occ = p.lstOccupation.occupation;

  //     const moment = occ.moment ? new Date(occ.moment) : null;
  //     const free = Number(occ.free);

  //     if (moment && !Number.isNaN(free)) {
  //       await prisma.parkingOccupancy.create({
  //         data: {
  //           parkingId: pid,
  //           moment,
  //           free,
  //         },
  //       });
  //     }
  //   }

  // }

  for (const p of list) {
    // Leer campos con namespace ns2:
    const pid = Number(p["ns2:id"]);
    const lat = Number(p["ns2:latitude"]);
    const lon = Number(p["ns2:longitude"]);

    if (!pid || Number.isNaN(pid)) {
      console.warn("⚠ Parking sin ID válido, se omite:", p);
      continue;
    }

    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      console.warn(`⚠ Parking ${pid} sin coordenadas válidas, se omite`);
      continue;
    }

    const safe = (v: any) => (v === undefined || v === null ? null : v);

    await prisma.parking.upsert({
      where: { id: pid },
      update: {
        name: safe(p["ns2:name"]),
        nickName: safe(p["ns2:nickName"]),
        address: safe(p["ns2:address"]),
        town: safe(p["ns2:town"]),
        state: safe(p["ns2:state"]),
        areaCode: safe(String(p["ns2:areaCode"])),
        latitude: lat,
        longitude: lon,
        category: safe(p["ns2:category"]),
        familyCode: safe(String(p["ns2:familyCode"])), // ← CORREGIDO
        type: safe(p["ns2:type"]),
      },
      create: {
        id: pid,
        name: safe(p["ns2:name"]),
        nickName: safe(p["ns2:nickName"]),
        address: safe(p["ns2:address"]),
        town: safe(p["ns2:town"]),
        state: safe(p["ns2:state"]),
        areaCode: safe(String(p["ns2:areaCode"])),
        latitude: lat,
        longitude: lon,
        category: safe(p["ns2:category"]),
        familyCode: safe(String(p["ns2:familyCode"])), // ← CORREGIDO
        type: safe(p["ns2:type"]),
      },
    });

    // Ocupación (también con namespace)
    const occ = p["ns2:lstOccupation"]?.["ns2:occupation"];
    if (occ) {
      const moment = occ["ns2:moment"] ? new Date(occ["ns2:moment"]) : null;
      const free = Number(occ["ns2:free"]);

      if (moment && !Number.isNaN(free)) {
        await prisma.parkingOccupancy.create({
          data: {
            parkingId: pid,
            moment,
            free,
          },
        });
      }
    }
  }

  const count = await prisma.parking.count();
  console.log("Parkings en MongoDB:", count);
  console.log("✅ Ingesta completada correctamente");
  await prisma.$disconnect();
}

ingest().catch(async (e) => {
  console.error("❌ Error en la ingesta:", e);
  await prisma.$disconnect();
});
