// Zertifikat-Generierung mit jsPDF
// Shared Modul für Frontend (Browser) und Backend (Node.js)

// Vertragsbedingungen (statisch)
const CONTRACT_TERMS = [
  "1. Der Kunde bestätigt, dass der Ledger Hardware Wallet ihm gehört.",
  "2. Die Tron-Adresse ist für die Eurozahlung freigegeben.",
  "3. Nach Zahlungseingang wird das Zertifikat finalisiert.",
  "4. Der Anwalt prüft das Zertifikat vor Freigabe der Zahlung.",
  "5. Missbrauch führt zum sofortigen Ausschluss."
];

// Zertifikat-ID generieren (UUID-ähnlich)
function generateCertificateId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    // Browser
    return crypto.randomUUID();
  } else if (typeof require !== 'undefined') {
    // Node.js
    const crypto = require('crypto');
    return crypto.randomUUID();
  } else {
    // Fallback
    return 'cert-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }
}

// jsPDF laden (Browser vs Node.js)
async function loadJsPDF() {
  if (typeof window !== 'undefined') {
    // Browser: jsPDF via CDN
    if (window.jspdf) {
      return window.jspdf.jsPDF;
    }
    // CDN laden
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    script.async = true;
    await new Promise((resolve, reject) => {
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return window.jspdf.jsPDF;
  } else {
    // Node.js: jsPDF via npm
    const { jsPDF } = require('jspdf');
    return jsPDF;
  }
}

// Zertifikat generieren
async function generateCertificate(data) {
  // data: { address, txID, date, email, from, to, certificateId }
  const jsPDF = await loadJsPDF();
  const doc = new jsPDF();

  const certId = data.certificateId || generateCertificateId();
  const date = data.date || new Date().toISOString();
  const formattedDate = new Date(date).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  });

  // Farben
  const primaryColor = [10, 92, 255]; // #0a5cff
  const textColor = [23, 32, 43]; // #17202b
  const mutedColor = [95, 107, 124]; // #5f6b7c

  // Header
  doc.setFillColor(...primaryColor);
  doc.rect(0, 0, 210, 40, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(24);
  doc.setFont('helvetica', 'bold');
  doc.text('Verification Certificate', 105, 25, { align: 'center' });

  // Branding
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text('chain scanner', 105, 33, { align: 'center' });

  // Content
  doc.setTextColor(...textColor);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Identity Verification Complete', 105, 60, { align: 'center' });

  doc.setTextColor(...mutedColor);
  doc.setFontSize(12);
  doc.setFont('helvetica', 'normal');
  doc.text('This document certifies that the identity verification process', 105, 70, { align: 'center' });
  doc.text('has been completed successfully.', 105, 78, { align: 'center' });

  // Info Box
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(227, 232, 239);
  doc.roundedRect(20, 90, 170, 70, 8, 8, 'FD');

  doc.setTextColor(...textColor);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('Verification Details', 30, 102);

  doc.setTextColor(...mutedColor);
  doc.setFont('helvetica', 'normal');
  
  let y = 115;
  if (data.to) {
    doc.text('Customer:', 30, y);
    doc.setFont('helvetica', 'bold');
    doc.text(data.to, 70, y);
    y += 8;
    doc.setFont('helvetica', 'normal');
  }
  
  if (data.from) {
    doc.text('Company:', 30, y);
    doc.setFont('helvetica', 'bold');
    doc.text(data.from, 70, y);
    y += 8;
    doc.setFont('helvetica', 'normal');
  }

  doc.text('Date:', 30, y);
  doc.setFont('helvetica', 'bold');
  doc.text(formattedDate, 70, y);
  y += 8;
  doc.setFont('helvetica', 'normal');

  if (data.address) {
    doc.text('TRON Address:', 30, y);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text(data.address, 70, y);
    y += 10;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
  }

  if (data.txID) {
    doc.text('Transaction ID:', 30, y);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text(data.txID, 70, y);
    y += 10;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
  }

  doc.text('Certificate ID:', 30, y);
  doc.setFont('helvetica', 'bold');
  doc.text(certId, 70, y);

  // Vertragsbedingungen
  doc.setTextColor(...textColor);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('Terms & Conditions', 20, 175);

  doc.setTextColor(...mutedColor);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  
  y = 185;
  CONTRACT_TERMS.forEach((term, index) => {
    doc.text(term, 25, y);
    y += 7;
  });

  // Footer
  doc.setFillColor(248, 250, 252);
  doc.rect(0, 250, 210, 47, 'F');
  
  doc.setTextColor(...mutedColor);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('This certificate is automatically generated after successful verification.', 105, 260, { align: 'center' });
  doc.text('Please forward this document to your attorney for payment release.', 105, 268, { align: 'center' });
  doc.text('Generated by Chainscaner · ' + formattedDate, 105, 285, { align: 'center' });

  // Approve Badge
  doc.setFillColor(20, 145, 75);
  doc.circle(175, 265, 15, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('✓', 175, 270, { align: 'center' });

  // Return PDF (Browser: Blob, Node: Buffer)
  if (typeof window !== 'undefined') {
    // Browser
    return {
      pdf: doc,
      blob: doc.output('blob'),
      certId: certId
    };
  } else {
    // Node.js
    return {
      pdf: doc,
      buffer: Buffer.from(doc.output('arraybuffer')),
      certId: certId
    };
  }
}

// Export für Browser und Node.js
if (typeof module !== 'undefined' && module.exports) {
  // Node.js
  module.exports = { generateCertificate, generateCertificateId };
} else {
  // Browser
  window.CertificateGenerator = { generateCertificate, generateCertificateId };
}
