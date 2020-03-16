import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

// Notice, do not import com.mysql.cj.jdbc.*
// or you will have problems!


public class Main {


    public static void main(String[] args) {
        Connection conn = null;

        try {
          conn =
             DriverManager.getConnection("jdbc:mysql://localhost/test?" +
                                       "user=minty&password=greatsqldb");

        } catch (SQLException ex) {
          System.out.println("SQLException: " + ex.getMessage());
          System.out.println("SQLState: " + ex.getSQLState());
          System.out.println("VendorError: " + ex.getErrorCode());
        }
    }
}
