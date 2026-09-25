// lab: ComposedFees
import java.math.BigDecimal;
public class ComposedFees {
  interface FeePolicy { BigDecimal fee(BigDecimal amount); }
  record Checkout(FeePolicy policy) {
    Checkout { java.util.Objects.requireNonNull(policy); }
    BigDecimal total(BigDecimal amount) {
      if (amount.signum()<0) throw new IllegalArgumentException("negative amount");
      return amount.add(policy.fee(amount));
    }
  }
  public static void main(String[] args) {
    var free = new Checkout(amount -> BigDecimal.ZERO);
    var flat = new Checkout(amount -> new BigDecimal("2.00"));
    assert free.total(new BigDecimal("10.00")).compareTo(new BigDecimal("10"))==0;
    assert flat.total(new BigDecimal("10.00")).compareTo(new BigDecimal("12"))==0;
    System.out.println("Fee behavior changes through composition; money uses decimal values.");
  }
}
