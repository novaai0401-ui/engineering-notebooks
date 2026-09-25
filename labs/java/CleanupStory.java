// lab: CleanupStory
public abstract class CleanupStory {
  abstract String describe();
  static class Resource implements AutoCloseable {
    public void close() { throw new IllegalStateException("close failure"); }
  }
  public static void main(String[] args) {
    try (var resource = new Resource()) {
      throw new IllegalArgumentException("body failure");
    } catch (IllegalArgumentException error) {
      assert error.getMessage().equals("body failure");
      assert error.getSuppressed().length == 1;
      System.out.println("Abstract main ran; body failure retained; close failure suppressed.");
    }
  }
}
