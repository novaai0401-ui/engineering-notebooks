package learning;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class PaymentServiceTest {
    @Test void calculatesAndSavesExactlyOnce() {
        var ledger = mock(PaymentService.Ledger.class);
        var service = new PaymentService(ledger);
        assertEquals(new BigDecimal("12.00"), service.charge(new BigDecimal("10.00")));
        verify(ledger).save(new BigDecimal("12.00"));
        verifyNoMoreInteractions(ledger);
    }
    @Test void invalidInputNeverTouchesLedger() {
        var ledger = mock(PaymentService.Ledger.class);
        assertThrows(IllegalArgumentException.class, () -> new PaymentService(ledger).charge(BigDecimal.ZERO));
        verifyNoInteractions(ledger);
    }
    @Test void persistenceFailureIsNotReportedAsSuccess() {
        var ledger = mock(PaymentService.Ledger.class);
        doThrow(new IllegalStateException("ledger unavailable")).when(ledger).save(any());
        assertThrows(IllegalStateException.class, () -> new PaymentService(ledger).charge(BigDecimal.ONE));
    }
}
