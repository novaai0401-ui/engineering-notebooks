// lab: FirstJava
public class FirstJava {
    static int total(int count, int price, int fee) {
        if (count < 0) throw new IllegalArgumentException("negative count");
        return Math.addExact(Math.multiplyExact(count, price), fee);
    }
    public static void main(String[] args) {
        if (total(3, 10, 5) != 35) throw new AssertionError();
        String a = new String("book");
        String b = new String("book");
        if (!a.equals(b)) throw new AssertionError();
        System.out.println("Total: 35; text values equal");
    }
}
