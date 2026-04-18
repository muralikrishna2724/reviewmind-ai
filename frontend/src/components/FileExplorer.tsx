import React, { useState } from "react";
import type { ProjectFile } from "../types";
import { FileCode, CheckCircle, AlertCircle, ChevronRight, ChevronDown } from "lucide-react";

interface Props {
  files: ProjectFile[];
  onFileSelect: (file: ProjectFile) => void;
  selectedFileId?: string;
}

interface TreeNode {
  name: string;
  path: string;
  file?: ProjectFile;
  children: Record<string, TreeNode>;
}

function buildTree(files: ProjectFile[]): TreeNode {
  const root: TreeNode = { name: "", path: "", children: {} };
  for (const f of files) {
    const parts = f.path.split("/");
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!node.children[part]) {
        node.children[part] = { name: part, path: parts.slice(0, i + 1).join("/"), children: {} };
      }
      node = node.children[part];
      if (i === parts.length - 1) node.file = f;
    }
  }
  return root;
}

function TreeNodeView({ node, depth, onSelect, selectedId }: {
  node: TreeNode; depth: number;
  onSelect: (f: ProjectFile) => void; selectedId?: string;
}) {
  const [open, setOpen] = useState(depth < 2);
  const isDir = !node.file && Object.keys(node.children).length > 0;
  const isFile = !!node.file;

  if (isFile) {
    const f = node.file!;
    return (
      <div
        onClick={() => onSelect(f)}
        className={`flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer text-xs transition-colors
          ${f.id === selectedId ? "bg-blue-900/50 text-blue-300" : "hover:bg-gray-800 text-gray-400"}`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {f.reviewed
          ? <CheckCircle size={11} className="text-green-500 shrink-0" />
          : <FileCode size={11} className="shrink-0" />}
        <span className="truncate">{node.name}</span>
      </div>
    );
  }

  if (isDir) {
    return (
      <div>
        <div
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-1 px-2 py-1 cursor-pointer text-xs text-gray-500 hover:text-gray-300"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          <span>{node.name}/</span>
        </div>
        {open && Object.values(node.children).map(child => (
          <TreeNodeView key={child.path} node={child} depth={depth + 1} onSelect={onSelect} selectedId={selectedId} />
        ))}
      </div>
    );
  }
  return null;
}

export default function FileExplorer({ files, onFileSelect, selectedFileId }: Props) {
  const tree = buildTree(files);
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden h-full">
      <div className="px-3 py-2 border-b border-gray-800 text-xs font-semibold text-gray-500 uppercase">
        Files ({files.length})
      </div>
      <div className="overflow-y-auto max-h-96 py-1">
        {Object.values(tree.children).map(child => (
          <TreeNodeView key={child.path} node={child} depth={0} onSelect={onFileSelect} selectedId={selectedFileId} />
        ))}
        {files.length === 0 && (
          <p className="text-xs text-gray-600 text-center py-4">No files</p>
        )}
      </div>
    </div>
  );
}
