package learning;
import java.math.BigDecimal;
import java.util.Objects;

/** Small SRP/composition example: orchestration depends on a persistence boundary. */
public final class PaymentService {
    public interface Ledger { void save(BigDecimal amount); }
    private final Ledger ledger;
    public PaymentService(Ledger ledger) { this.ledger = Objects.requireNonNull(ledger); }
    public BigDecimal charge(BigDecimal amount) {
        if (amount == null || amount.signum() <= 0) throw new IllegalArgumentException("positive amount required");
        var total = amount.add(new BigDecimal("2.00"));
        ledger.save(total);
        return total;
    }
}
