package pl.ksef.pdf;

import io.alapierre.ksef.fop.InvoiceGenerationParams;
import io.alapierre.ksef.fop.InvoiceSchema;
import io.alapierre.ksef.fop.PdfGenerator;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/v1")
public class PdfController {

    private static final int MAX_XML_SIZE = 10 * 1024 * 1024;

    private final PdfGenerator pdfGenerator;

    public PdfController() throws Exception {
        this.pdfGenerator = new PdfGenerator("fop.xconf");
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
        @RequestParam(defaultValue = "pl") String language
    ) throws Exception {

        if (invoiceXml.length == 0) {
            throw new IllegalArgumentException("XML cannot be empty");
        }

        if (invoiceXml.length > MAX_XML_SIZE) {
            throw new IllegalArgumentException("XML exceeds 10 MB limit");
        }

        InvoiceGenerationParams params = InvoiceGenerationParams.builder()
            .schema(InvoiceSchema.FA3_1_0_E)
            .ksefNumber(ksefNumber)
            .languageLocale(language)
            .build();

        ByteArrayOutputStream output = new ByteArrayOutputStream();

        pdfGenerator.generateInvoice(invoiceXml, params, output);

        String filename = ksefNumber + ".pdf";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_PDF);
        headers.setContentDisposition(
            ContentDisposition.inline()
                .filename(filename, StandardCharsets.UTF_8)
                .build()
        );

        return ResponseEntity
            .ok()
            .headers(headers)
            .body(output.toByteArray());
    }
}
