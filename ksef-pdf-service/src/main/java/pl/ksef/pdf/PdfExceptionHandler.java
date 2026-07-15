package pl.ksef.pdf;

import io.alapierre.ksef.fop.qr.exceptions.QrCodeGenerationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class PdfExceptionHandler {

    @ExceptionHandler(QrCodeGenerationException.class)
    public ResponseEntity<Map<String, String>> handleQrError(
        QrCodeGenerationException exception
    ) {
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(Map.of(
            "detail", exception.getMessage()
        ));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> handleValidationError(
        IllegalArgumentException exception
    ) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
            "detail", exception.getMessage()
        ));
    }
}
