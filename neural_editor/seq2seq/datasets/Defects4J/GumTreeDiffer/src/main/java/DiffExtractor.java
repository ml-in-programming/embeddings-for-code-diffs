import com.github.gumtreediff.gen.Generators;
import com.github.gumtreediff.matchers.Matcher;
import com.github.gumtreediff.matchers.Matchers;
import com.github.gumtreediff.tree.ITree;
import com.github.gumtreediff.tree.TreeContext;
import org.jetbrains.annotations.Contract;
import org.jetbrains.annotations.NotNull;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import static org.eclipse.jdt.core.dom.ASTNode.METHOD_DECLARATION;
import static org.eclipse.jdt.core.dom.ASTNode.SIMPLE_NAME;


class DiffExtractor {
    private Path root;
    private String prevFileText;
    private String updatedFileText;
    private TreeContext prevContext;
    private TreeContext updatedContext;
    private Matcher matcher;

    DiffExtractor(@NotNull Path root) throws IOException {
        this.root = root;
        Path prev = root.resolve("prev.java");
        Path updated = root.resolve("updated.java");
        prevFileText = Files.readString(prev);
        updatedFileText = Files.readString(updated);
        prevContext = Generators.getInstance().getTree(prev.toAbsolutePath().toString());
        updatedContext = Generators.getInstance().getTree(updated.toAbsolutePath().toString());
        matcher = Matchers.getInstance().getMatcher(prevContext.getRoot(), updatedContext.getRoot());
        matcher.match();
    }

    @NotNull
    private List<MethodDiff> extractMethodDiffs() {
        List<MethodDiff> methodDiffs = new ArrayList<>();
        extractMethodDiffsRecursively(prevContext.getRoot(), methodDiffs);
        return methodDiffs;
    }

    private void extractMethodDiffsRecursively(ITree prev, List<MethodDiff> result) {
        ITree updated = matcher.getMappings().getDst(prev);
        if (prev.getType() == METHOD_DECLARATION && updated.getType() == METHOD_DECLARATION) {
            result.add(new MethodDiff(prev, updated));
        }
        for (ITree child: prev.getChildren()) {
            extractMethodDiffsRecursively(child, result);
        }
    }

    void saveMethodDiffs() throws IOException {
        List<MethodDiff> methodDiffs = extractMethodDiffs();
        if (methodDiffs.isEmpty()) {
            return;
        }
        Path currentDir = root.resolve("method_pairs");
        Files.createDirectory(currentDir);
        for (MethodDiff methodDiff: methodDiffs) {
            Path dirToWriteFiles = currentDir.resolve(methodDiff.getMethodName());
            Files.createDirectory(dirToWriteFiles);
            Files.writeString(dirToWriteFiles.resolve("prev_method.java"), methodDiff.getPrev());
            Files.writeString(dirToWriteFiles.resolve("updated_method.java"), methodDiff.getUpdated());
        }
    }

    private class MethodDiff {
        private String methodName;
        private String prev;
        private String updated;

        @Contract(pure = true)
        private MethodDiff(ITree prevMethod, ITree updatedMethod) {
            prev = getNodeText(prevMethod, prevFileText);
            updated = getNodeText(updatedMethod, updatedFileText);
            methodName = getMethodName(prevMethod, prevContext);
            if (!getMethodName(updatedMethod, updatedContext).equals(methodName)) {
                System.out.println("WARNING!");
                System.out.println("Method name in prev code does not equals to method name in updated code.");
            }
        }

        private String getNodeText(ITree node, String fileContent) {
            return fileContent.substring(node.getPos(), node.getEndPos());
        }

        private String getMethodName(ITree methodNode, TreeContext context) {
            List<String> methodNames = methodNode.getChildren().stream()
                    .filter(child -> child.getType() == SIMPLE_NAME)
                    .map(ITree::getLabel)
                    .collect(Collectors.toList());
            if (methodNames.size() == 0) {
                System.out.println("WARNING!");
                System.out.println("No method name found!");
                return "NoMethodNameFound_" + methodNode.hashCode();
            }
            else if (methodNames.size() > 1) {
                System.out.println("WARNING!");
                System.out.println("More than one method names are found!");
                System.out.println("Possible names: " + String.join(", ", methodNames) + ".");
                System.out.println("First variant will be taken.");
            }
            return methodNames.get(0);
        }

        @Contract(pure = true)
        private MethodDiff(String methodName, String prev, String updated) {
            this.methodName = methodName;
            this.prev = prev;
            this.updated = updated;
        }

        @Contract(pure = true)
        private String getMethodName() {
            return methodName;
        }

        @Contract(pure = true)
        private String getPrev() {
            return prev;
        }

        @Contract(pure = true)
        private String getUpdated() {
            return updated;
        }
    }
}
