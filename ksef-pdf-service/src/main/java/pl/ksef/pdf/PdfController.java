package pl.ksef.pdf;

import io.alapierre.ksef.fop.InvoiceGenerationParams;
import io.alapierre.ksef.fop.InvoiceQRCodeGeneratorRequest;
import io.alapierre.ksef.fop.InvoiceSchema;
import io.alapierre.ksef.fop.PdfGenerator;
import io.alapierre.ksef.fop.qr.VerificationLinkGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/v1")
public class PdfController {

    private static final Logger log = LoggerFactory.getLogger(PdfController.class);
    private static final int MAX_XML_SIZE = 10 * 1024 * 1024;

    private final PdfGenerator pdfGenerator;

    public PdfController() throws Exception {
        this.pdfGenerator = new PdfGenerator("fop.xconf");
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of(
            "status", "ok",
            "qrEnabled", true
        );
    }

    @PostMapping(
        value = "/invoices/pdf",
        consumes = {
            MediaType.APPLICATION_XML_VALUE,
            MediaType.TEXT_XML_VALUE
        },
        produces = MediaType.APPLICATION_PDF_VALUE
    )
    public ResponseEntity<byte[]> generatePdf(
        @RequestBody byte[] invoiceXml,
        @RequestParam String ksefNumber,
        @RequestParam String sellerNip,
        @RequestParam
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        LocalDate issueDate,
        @RequestParam String qrBaseUrl,
        @RequestParam(defaultValue = "pl") String language
    ) throws Exception {

        if (invoiceXml.length == 0) {
            throw new IllegalArgumentException("XML cannot be empty");
        }

        if (invoiceXml.length > MAX_XML_SIZE) {
            throw new IllegalArgumentException("XML exceeds 10 MB limit");
        }

        String verificationLink = VerificationLinkGenerator.generateVerificationLink(
            qrBaseUrl,
            sellerNip,
            issueDate,
            invoiceXml
        );

        log.info(
            "Generating PDF with QR for ksefNumber={}, nip={}, issueDate={}, qrBaseUrl={}",
            ksefNumber,
            sellerNip,
            issueDate,
            qrBaseUrl
        );
        log.debug("Verification link: {}", verificationLink);

        InvoiceQRCodeGeneratorRequest qrRequest =
            InvoiceQRCodeGeneratorRequest.onlineQrBuilder(verificationLink);

        InvoiceGenerationParams params =
            InvoiceGenerationParams.builder()
                .schema(InvoiceSchema.FA3_1_0_E)
                .ksefNumber(ksefNumber)
                .invoiceQRCodeGeneratorRequest(qrRequest)
                .languageLocale(language)
                .build();

        ByteArrayOutputStream output = new ByteArrayOutputStream();

        pdfGenerator.generateInvoice(
            invoiceXml,
            params,
            output
        );

        String filename = ksefNumber + ".pdf";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_PDF);
        headers.setContentDisposition(
            ContentDisposition.attachment()
                .filename(filename, StandardCharsets.UTF_8)
                .build()
        );
        headers.add("X-KSeF-Verification-Link", verificationLink);

        return ResponseEntity
            .ok()
            .headers(headers)
            .body(output.toByteArray());
    }
}
