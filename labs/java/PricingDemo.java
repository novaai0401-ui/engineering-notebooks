// lab: PricingDemo
public class PricingDemo {
    interface Pricing { int price(int quantity); }
    record FlatPricing(int unitPrice) implements Pricing {
        FlatPricing {
            if (unitPrice < 0) throw new IllegalArgumentException();
        }
        public int price(int quantity) {
            if (quantity < 0) throw new IllegalArgumentException();
            return Math.multiplyExact(unitPrice, quantity);
        }
    }
    static int checkout(Pricing pricing, int quantity) {
        return pricing.price(quantity);
    }
    public static void main(String[] args) {
        if (checkout(new FlatPricing(7), 3) != 21) throw new AssertionError();
        System.out.println("Strategy supplied through an interface");
    }
}
