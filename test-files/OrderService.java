public class OrderService {

    public void processOrder(String item) {
        Inventory inv = new Inventory();
        inv.reduceStock(item);
    }
}

class Inventory {

    public void reduceStock(String item) {
        System.out.println("Stock reduced for: " + item);
    }
}